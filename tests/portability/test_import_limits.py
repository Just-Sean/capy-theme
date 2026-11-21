"""Limits and clean errors for theme imports (issue #236)."""

import io
import json
import tracemalloc
import zipfile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from capy_theme.models import Font, Theme
from capy_theme.portability import importing
from capy_theme.portability.export import FORMAT
from capy_theme.portability.importing import import_theme
from tests.support.google import woff2

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    return tmp_path


def manifest(fonts=None):
    return {
        "format": FORMAT,
        "theme": {
            "name": "Imported",
            "slug": "imported",
            "base": "light",
            "settings": {},
        },
        "fonts": fonts or {},
        "images": {},
    }


def font_entry(*paths):
    return {
        "family": "Brand Sans",
        "source": "upload",
        "files": [{"path": path, "weight": 400, "style": "normal"} for path in paths],
    }


def export_zip(data, files=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.json", json.dumps(data))
        for name, content in (files or {}).items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_a_file_used_more_than_once_is_refused(media):
    data = manifest({"font-1": font_entry("fonts/1-0.woff2", "fonts/1-0.woff2")})
    upload = io.BytesIO(export_zip(data, {"fonts/1-0.woff2": woff2()}))
    with pytest.raises(ValidationError, match="uses fonts/1-0.woff2 more than once"):
        import_theme(upload)
    assert not Theme.objects.exists()
    assert not Font.objects.filter(family="Brand Sans").exists()
    assert not [path for path in media.rglob("*") if path.is_file()]


def test_each_file_used_once_still_imports():
    data = manifest({"font-1": font_entry("fonts/1-0.woff2", "fonts/1-1.woff2")})
    files = {"fonts/1-0.woff2": woff2(), "fonts/1-1.woff2": woff2()}
    theme = import_theme(io.BytesIO(export_zip(data, files)))
    assert Font.objects.get(family="Brand Sans").files.count() == 2
    assert theme.name == "Imported"


def test_an_export_with_the_reserved_slug_gets_a_free_one():
    # Exports from before 1.0 may use "default", which visitors' picker reserves (#254).
    data = manifest()
    data["theme"]["slug"] = "default"
    theme = import_theme(io.BytesIO(export_zip(data)))
    assert theme.slug == "default-imported"


def test_a_damaged_zip_entry_is_a_clear_message_not_a_server_error():
    data = manifest({"font-1": font_entry("fonts/1-0.woff2")})
    # Change one byte of the stored font, so its checksum no longer matches.
    damaged = bytearray(export_zip(data, {"fonts/1-0.woff2": b"x" * 200}))
    damaged[damaged.index(b"x" * 200) + 10] = ord("y")
    with pytest.raises(ValidationError, match="The export is damaged"):
        import_theme(io.BytesIO(bytes(damaged)))


@pytest.mark.parametrize(
    "error",
    [
        zipfile.BadZipFile("Bad CRC-32"),
        RuntimeError("File is encrypted, password required"),
        NotImplementedError("That compression method is not supported"),
        EOFError(),
    ],
)
def test_every_kind_of_unreadable_entry_is_a_clear_message(monkeypatch, error):
    def unreadable(self, name, mode="r", pwd=None, **kwargs):
        raise error

    data = export_zip(manifest())  # written before reading breaks
    monkeypatch.setattr(zipfile.ZipFile, "open", unreadable)
    with pytest.raises(ValidationError, match="The export is damaged"):
        import_theme(io.BytesIO(data))


def test_an_upload_over_the_limit_is_refused_before_it_is_opened(settings, monkeypatch):
    settings.CAPY_THEME_IMPORT_MAX_BYTES = 100
    opened = []
    monkeypatch.setattr(importing.zipfile, "ZipFile", lambda *args: opened.append(args))
    upload = SimpleUploadedFile("theme.zip", b"z" * 101)
    with pytest.raises(ValidationError, match="too big"):
        import_theme(upload)
    assert not opened


def test_a_zip_with_too_many_files_is_refused(settings):
    settings.CAPY_THEME_IMPORT_MAX_FILES = 3
    files = {f"images/{n}.png": b"" for n in range(3)}  # with theme.json: 4 files
    with pytest.raises(ValidationError, match="too many files"):
        import_theme(io.BytesIO(export_zip(manifest(), files)))
    settings.CAPY_THEME_IMPORT_MAX_FILES = 4
    import_theme(io.BytesIO(export_zip(manifest(), files)))


# A zip entry that understates its size must not be unpacked in full (#251).


def lying_zip(method, megabytes):
    """A theme.json padded with `megabytes` MB of spaces whose stated size is 10 bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", method) as archive:
        with archive.open("theme.json", "w") as entry:
            entry.write(json.dumps(manifest()).encode())
            for _ in range(megabytes):
                entry.write(b" " * (1024 * 1024))
    data = bytearray(buffer.getvalue())
    data[22:26] = (10).to_bytes(4, "little")  # the local header's unpacked size
    central = bytes(data).rfind(b"PK\x01\x02")
    data[central + 24 : central + 28] = (10).to_bytes(4, "little")  # and the central one
    return bytes(data)


def peak_memory_while_importing(data):
    tracemalloc.start()
    try:
        with pytest.raises(ValidationError, match="The export is damaged"):
            import_theme(io.BytesIO(data))
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_deflate_entry_that_lies_about_its_size_is_refused_not_unpacked():
    data = lying_zip(zipfile.ZIP_DEFLATED, 200)
    assert len(data) < 1024 * 1024
    assert peak_memory_while_importing(data) < 5 * 1024 * 1024


def test_a_bzip2_entry_is_refused_before_it_is_unpacked():
    # bzip2 (and LZMA) can't be unpacked a bounded amount at a time; exports never use them.
    data = lying_zip(zipfile.ZIP_BZIP2, 300)
    assert len(data) < 100 * 1024
    assert peak_memory_while_importing(data) < 5 * 1024 * 1024


def test_an_honest_entry_still_imports_after_the_bounded_read():
    theme = import_theme(io.BytesIO(export_zip(manifest())))
    assert theme.slug == "imported"
