"""Importing a theme exported by capy-theme (see export.py) as a new draft.

Everything is checked before it's stored: the zip's size and names, theme.json
against theme_file.schema.json, the bases and settings like any theme, images
through the same checks as uploads, and font files like font uploads. Nothing
is published or activated. If anything fails, nothing is kept.
"""

import json
import zipfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from jsonschema import Draft7Validator

from .. import conf
from ..fonts.models import Font, FontFile
from ..fonts.uploads import prepare
from ..images.uploads import add_asset
from ..themes.models.theme import Theme

SCHEMA = json.loads(Path(__file__).with_name("theme_file.schema.json").read_text(encoding="utf-8"))


def import_theme(upload, keep_custom_css=True):
    """Create a new, unpublished theme from an export zip. Returns the Theme.

    `upload` is a file object (e.g. an uploaded file). Without `keep_custom_css`
    (the importer can't edit custom CSS), the export's custom CSS is left out.
    Raises ValidationError with a readable message if the file isn't a valid
    capy-theme export.
    """
    archive = _open(upload)
    manifest = _manifest(archive)
    if not keep_custom_css:
        manifest["theme"]["settings"].pop("custom_css", None)
    stored = []  # files saved so far, deleted again if the import fails
    try:
        with transaction.atomic():
            return _create(archive, manifest, stored)
    except Exception:
        for field_file in stored:
            field_file.delete(save=False)
        raise


def _open(upload):
    try:
        archive = zipfile.ZipFile(upload)
    except zipfile.BadZipFile as error:
        raise ValidationError("That isn't a zip file.") from error
    limit = conf.get("CAPY_THEME_IMPORT_MAX_BYTES")  # all files in the zip, unpacked
    if sum(info.file_size for info in archive.infolist()) > limit:
        raise ValidationError(f"The export is too big (over {limit // 1024 // 1024} MB).")
    return archive


def _read(archive, name):
    try:
        return archive.read(name)
    except KeyError as error:
        raise ValidationError(f"The export is missing {name}.") from error


def _manifest(archive):
    try:
        manifest = json.loads(_read(archive, "theme.json"))
    except ValueError as error:
        raise ValidationError("theme.json isn't valid JSON.") from error
    problems = sorted(e.message for e in Draft7Validator(SCHEMA).iter_errors(manifest))
    if problems:
        raise ValidationError(["theme.json isn't a capy-theme export:", *problems[:5]])
    return manifest


def _create(archive, manifest, stored):
    data = manifest["theme"]
    theme = Theme.objects.create(
        name=_free("name", data["name"]),
        slug=_free("slug", data["slug"]),
        light_base=data["light_base"],
        dark_base=data["dark_base"],
        settings=data["settings"],
    )
    fonts = {key: _font(archive, font, stored) for key, font in manifest["fonts"].items()}
    images = {}
    for key, image in manifest["images"].items():
        upload = SimpleUploadedFile(Path(image["path"]).name, _read(archive, image["path"]))
        asset = add_asset(theme, image["slot"], image["mode"], upload, image.get("alt_text", ""))
        stored.append(asset.original)
        stored.extend(variant.file for variant in asset.variants.all())
        images[key] = asset.pk
    settings = dict(data["settings"])
    if data.get("font_roles"):
        settings["fonts"] = {role: _known(fonts, key) for role, key in data["font_roles"].items()}
    if data.get("image_slots"):
        settings["images"] = {
            slot: {mode: _known(images, key) for mode, key in modes.items()}
            for slot, modes in data["image_slots"].items()
        }
    theme.settings = settings
    theme.save()  # validates the settings and bases like any theme
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
