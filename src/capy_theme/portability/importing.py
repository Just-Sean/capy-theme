"""Importing a theme exported by capy-theme (see export.py) as a new draft.

Everything is checked before it's stored: the zip's size and names, theme.json
against theme_file.schema.json, the bases and settings like any theme, images
through the same checks as uploads, and font files like font uploads. Nothing
is published or activated. If anything fails, nothing is kept.
"""

import json
import logging
import zipfile
import zlib
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from jsonschema import Draft7Validator

from .. import conf
from ..fonts.models import Font, FontFile
from ..fonts.uploads import prepare
from ..images.uploads import add_asset
from ..themes.models.theme import RESERVED_SLUG, Theme

logger = logging.getLogger(__name__)

SCHEMA = json.loads(Path(__file__).with_name("theme_file.schema.json").read_text(encoding="utf-8"))


def import_theme(upload, keep_custom_css=True, can_add_external_fonts=True):
    """Create a new, unpublished theme from an export zip. Returns the Theme.

    `upload` is a file object (e.g. an uploaded file). Without `keep_custom_css`
    (the importer can't edit custom CSS), the export's custom CSS is left out.
    Without `can_add_external_fonts` (the importer can't add fonts), an export that
    would add an external font (a stylesheet from another site, loaded on every
    page) is refused. Raises ValidationError with a readable message if the file
    isn't a valid capy-theme export.
    """
    archive = _open(upload)
    manifest = _manifest(archive)
    if not keep_custom_css:
        manifest["theme"]["settings"].pop("custom_css", None)
    if not can_add_external_fonts:
        _refuse_new_external_fonts(manifest)
    stored = []  # files saved so far, deleted again if the import fails
    try:
        with transaction.atomic():
            theme = _create(archive, manifest, stored)
    except Exception:
        for field_file in stored:
            field_file.delete(save=False)
        raise
    logger.info("Imported theme %r as an unpublished draft.", theme.slug)
    return theme


# What reading a damaged zip entry raises: a bad checksum or size, an encrypted
# entry, or a compression method Python can't unpack.
ALLOWED_COMPRESSION = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
DAMAGED_ZIP_ERRORS = (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError)


def _open(upload):
    limit = conf.get("CAPY_THEME_IMPORT_MAX_BYTES")  # the zip itself, and all its files unpacked
    too_big = ValidationError(f"The export is too big (over {limit // 1024 // 1024} MB).")
    if getattr(upload, "size", None) is not None and upload.size > limit:
        raise too_big
    try:
        archive = zipfile.ZipFile(upload)
    except zipfile.BadZipFile as error:
        raise ValidationError("That isn't a zip file.") from error
    members = archive.infolist()
    # Exports only use deflate (or none). Other methods (bzip2, LZMA) can't be
    # unpacked a bounded amount at a time, so they're refused (#251).
    if any(info.compress_type not in ALLOWED_COMPRESSION for info in members):
        raise ValidationError("The export is damaged.")
    max_files = conf.positive_int("CAPY_THEME_IMPORT_MAX_FILES")
    if len(members) > max_files:
        raise ValidationError(f"The export has too many files (over {max_files}).")
    if sum(info.file_size for info in members) > limit:
        raise too_big
    return archive


def _read(archive, name):
    """Read one file, never unpacking more than the size the zip says it has.

    A crafted entry can claim a few bytes and unpack to gigabytes; reading at most
    its stated size (plus one byte) keeps memory bounded, and zipfile then refuses
    it as damaged (its checksum doesn't match) (#251).
    """
    try:
        info = archive.getinfo(name)
        with archive.open(info) as entry:
            data = entry.read(info.file_size + 1)
        if len(data) != info.file_size:
            raise zipfile.BadZipFile("unpacked size differs from the stated size")
        return data
    except KeyError as error:
        raise ValidationError(f"The export is missing {name}.") from error
    except DAMAGED_ZIP_ERRORS as error:
        raise ValidationError("The export is damaged.") from error


def _manifest(archive):
    try:
        manifest = json.loads(_read(archive, "theme.json"))
    except ValueError as error:
        raise ValidationError("theme.json isn't valid JSON.") from error
    problems = sorted(e.message for e in Draft7Validator(SCHEMA).iter_errors(manifest))
    if problems:
        raise ValidationError(["theme.json isn't a capy-theme export:", *problems[:5]])
    _refuse_reused_paths(manifest)
    return manifest


def _refuse_new_external_fonts(manifest):
    """External fonts the library doesn't have yet need permission to add fonts (#235)."""
    for font in manifest["fonts"].values():
        if font["source"] == "external" and not Font.objects.filter(family=font["family"]).exists():
            raise ValidationError(
                f"The export adds the external font {font['family']}, which loads a "
                "stylesheet from another site. Importing it needs permission to add fonts."
            )


def _refuse_reused_paths(manifest):
    """Each file in the zip may be used once: otherwise one small file could be
    checked, converted and stored hundreds of times."""
    paths = [image["path"] for image in manifest["images"].values()]
    paths += [item["path"] for font in manifest["fonts"].values() for item in font["files"]]
    seen = set()
    for path in paths:
        if path in seen:
            raise ValidationError(f"theme.json uses {path} more than once.")
        seen.add(path)


def _create(archive, manifest, stored):
    data = manifest["theme"]
    theme = Theme.objects.create(
        name=_free("name", data["name"]),
        slug=_free("slug", data["slug"]),
        base=data["base"],
        settings=data["settings"],
    )
    fonts = {key: _font(archive, font, stored) for key, font in manifest["fonts"].items()}
    images = {}
    for key, image in manifest["images"].items():
        upload = SimpleUploadedFile(Path(image["path"]).name, _read(archive, image["path"]))
        asset = add_asset(theme, image["slot"], upload, image.get("alt_text", ""))
        stored.append(asset.original)
        stored.extend(variant.file for variant in asset.variants.all())
        images[key] = asset.pk
    settings = dict(data["settings"])
    if data.get("font_roles"):
        settings["fonts"] = {role: _known(fonts, key) for role, key in data["font_roles"].items()}
    if data.get("image_slots"):
        settings["images"] = {
            slot: _known(images, key) for slot, key in data["image_slots"].items()
        }
    theme.settings = settings
    theme.save()  # validates the settings and base like any theme
    return theme


def _font(archive, font, stored):
    """The library's font with this family, or a new one from the export's files."""
    existing = Font.objects.filter(family=font["family"]).first()
    if existing is not None:
        return existing.pk
    new = Font(
        family=font["family"],
        source=font["source"],
        fallback_stack=font.get("fallback_stack", ""),
        # Exports made before 1.0 call it "licence" (renamed in #199).
        license=font.get("license", font.get("licence", "")),
        stylesheet_url=font.get("stylesheet_url", ""),
    )
    new.full_clean()
    new.save()
    for item in font["files"]:
        checked = prepare(_read(archive, item["path"]), Path(item["path"]).name)
        font_file = FontFile(
            font=new,
            weight=item["weight"],
            style=item["style"],
            subset=item.get("subset", "latin") or "latin",
            unicode_range=item.get("unicode_range", ""),
        )
        font_file.file.save(checked["file"].name, checked["file"], save=False)
        stored.append(font_file.file)
        font_file.save()
    return new.pk


def _known(mapping, key):
    if key not in mapping:
        raise ValidationError(f"theme.json refers to {key}, which isn't in the export.")
    return mapping[key]


def _free(field, value):
    """`value`, or with " (imported)" / "-imported" added until no theme has it."""
    taken = set(Theme.objects.values_list(field, flat=True))
    if field == "slug":
        taken.add(RESERVED_SLUG)  # an export from before 1.0 may use it (#254)
    if value not in taken:
        return value
    suffix = " (imported{})" if field == "name" else "-imported{}"
    number = 1
    while True:
        candidate = value + suffix.format("" if number == 1 else f" {number}")
        candidate = candidate.replace(" ", "-") if field == "slug" else candidate
        if candidate not in taken:
            return candidate[:100]
        number += 1
