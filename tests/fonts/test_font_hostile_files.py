"""Edge cases for the font limits (#191): real fonts still accepted, every hostile shape refused."""

import io
import json
import struct
import zipfile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import WOFF2FlavorData

from capy_theme.fonts import converting, unpacking
from capy_theme.fonts.google import import_family
from capy_theme.fonts.models import Font, FontFile
from capy_theme.fonts.uploads import PARSE_ERRORS, prepare
from capy_theme.models import Theme
from capy_theme.portability.importing import import_theme
from tests.support.fonts import CHARACTERS, noise, real_font_with_extra, ttf_bytes, woff, woff2
from tests.support.google import FakeGoogle

MB = 1024 * 1024
SIZE_FIELD = 16  # where WOFF and WOFF2 headers keep totalSfntSize


@pytest.fixture(autouse=True)
def small_limit(settings, tmp_path):
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = MB
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def otf_bytes():
    """A small valid CFF-based OpenType font."""
    builder = FontBuilder(1000, isTTF=False)
    glyphs = [".notdef", *CHARACTERS]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({code: name for name, code in CHARACTERS.items()})
    pen = T2CharStringPen(600, None)
    pen.moveTo((100, 0))
    pen.lineTo((100, 700))
    pen.lineTo((500, 700))
    pen.closePath()
    charstring = pen.getCharString()
    builder.setupCFF("TestOTF", {"FullName": "Test OTF"}, dict.fromkeys(glyphs, charstring), {})
    builder.setupHorizontalMetrics({name: (600, 100) for name in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test OTF", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    out = io.BytesIO()
    builder.save(out)
    return out.getvalue()


def flavored(data, flavor, meta=None):
    font = TTFont(io.BytesIO(data))
    font.flavor = flavor
    if meta is not None:
        if flavor == "woff2":
            font.flavorData = WOFF2FlavorData()
        else:
            from fontTools.ttLib.sfnt import WOFFFlavorData

            font.flavorData = WOFFFlavorData()
        font.flavorData.metaData = meta
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def declared_size(data):
    return struct.unpack_from(">L", data, SIZE_FIELD)[0]


# Real fonts of every kind are still accepted


@pytest.mark.parametrize("base", [ttf_bytes, otf_bytes], ids=["truetype", "cff"])
@pytest.mark.parametrize("flavor", [None, "woff", "woff2"])
@pytest.mark.parametrize("subset", ["all", "latin"])
def test_every_kind_of_real_font_is_still_accepted(base, flavor, subset):
    data = base() if flavor is None else flavored(base(), flavor)
    result = prepare(data, "f.woff2", subset)
    assert result["file"].read()[:4] == b"wOF2"


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_large_real_font_just_under_the_limit_is_accepted(flavor, settings):
    """A font whose data doesn't compress, close to the limit, is not mistaken for a bomb."""
    data = real_font_with_extra(flavor, 1_500_000, fill=noise(1_500_000))
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = declared_size(data) + 1000
    assert prepare(data, "big.woff2", "latin")["file"].read()[:4] == b"wOF2"


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_real_font_exactly_at_the_limit_is_accepted_and_one_byte_over_refused(flavor, settings):
    data = real_font_with_extra(flavor, 200_000)
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = declared_size(data)
    assert prepare(data, "f.woff2")["file"].read()[:4] == b"wOF2"
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = declared_size(data) - 1
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(data, "f.woff2")


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_real_font_with_metadata_is_accepted(flavor):
    meta = b'<?xml version="1.0"?><metadata version="1.0"><uniqueid id="x"/></metadata>'
    assert prepare(flavored(ttf_bytes(), flavor, meta), "f.woff2")["file"].read()[:4] == b"wOF2"


# Hand-made odd files


@pytest.mark.parametrize("make", [woff2, woff])
def test_the_declared_size_exactly_at_the_limit_isnt_called_too_big(make, settings):
    honest = make(1000, 1000)
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = declared_size(honest)
    with pytest.raises(ValidationError) as caught:
        prepare(honest, "f.woff2")  # not a real font, but not refused for its size
    assert "too big" not in str(caught.value)
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = declared_size(honest) - 1
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(honest, "f.woff2")


def zero_tables(signature):
    if signature == b"wOF2":
        fields = (b"wOF2", b"\0\1\0\0", 48, 0, 0, 12, 0, 1, 0, 0, 0, 0, 0, 0)
        return struct.pack(">4s4sLHHLLHHLLLLL", *fields)
    return struct.pack(">4sLLHHLHHLLLLL", b"wOFF", 0x10000, 44, 0, 0, 12, 1, 0, 0, 0, 0, 0, 0)


@pytest.mark.parametrize("signature", [b"wOF2", b"wOFF"])
def test_a_file_with_no_tables_is_not_a_font(signature):
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(zero_tables(signature), "empty.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_a_metadata_only_bomb_is_refused(make):
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        prepare(make(0, 0, meta=(8 * MB, 1000)), "meta.woff2")


def woff_with_many_tables(count, declared_each, zeros):
    """A WOFF whose tables all point at one zlib stream of `zeros` bytes."""
    import zlib

    packed = zlib.compress(b"\0" * zeros, 9)
    start = 44 + 20 * count
    header = struct.pack(
        ">4sLLHHLHHLLLLL",
        *(b"wOFF", 0x10000, start + len(packed), count, 0, 12, 1, 0, 0, 0, 0, 0, 0),
    )
    tables = b"".join(
        struct.pack(">4sLLLL", f"t{n:03d}".encode(), start, len(packed), declared_each, 0)
        for n in range(count)
    )
    return header + tables + packed


def test_many_small_tables_adding_up_past_the_limit_are_refused():
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(woff_with_many_tables(40, 100_000, 100_000), "many.woff")


def test_many_tables_sharing_one_bomb_are_refused():
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        prepare(woff_with_many_tables(20, 40_000, 4 * MB), "many.woff")


# Damaged files: always "isn't a font", never another exception


def small(flavor):
    return flavored(ttf_bytes(), flavor)


def what_prepare_does(data, subset="all"):
    """prepare()'s steps, run here rather than in their own process, for speed.

    Returns "refused" or "accepted"; anything else it raises would be a 500.
    The tests below run it on thousands of files, which would take minutes with a
    process each. The separate process runs exactly `converting.outcome`.
    """
    try:
        unpacking.check(data)
    except (ValidationError, *PARSE_ERRORS):
        return "refused"
    return "accepted" if "font" in converting.outcome(data, subset) else "refused"


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_file_cut_short_anywhere_is_not_a_font(flavor):
    data = small(flavor)
    escaped = {}
    for length in range(len(data)):
        try:
            if what_prepare_does(data[:length]) == "accepted":
                escaped[length] = "accepted"
        except Exception as error:  # collect what escapes
            escaped[length] = repr(error)
    assert not escaped


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
@pytest.mark.parametrize("subset", ["all", "latin"])
def test_a_file_with_any_one_byte_damaged_is_not_a_font_or_still_a_font(flavor, subset):
    data = small(flavor)
    escaped = {}
    for offset in range(len(data)):
        for value in (0x00, 0xFF):
            damaged = bytearray(data)
            damaged[offset] = value
            try:
                what_prepare_does(bytes(damaged), subset)
            except Exception as error:  # collect what escapes
                escaped[(offset, value)] = repr(error)[:120]
    assert not escaped, f"{len(escaped)} damaged files raised: {list(escaped.items())[:5]}"


def woff_with_cut_stream():
    """A real WOFF whose extra table's zlib stream says it's 10 bytes shorter than it is.

    The check unpacks it without complaint (it stops early), and fontTools only
    unpacks that table later, when it saves the font as WOFF2.
    """
    data = bytearray(real_font_with_extra("woff", 100_000))
    count = struct.unpack_from(">H", data, 12)[0]
    for n in range(count):
        place = 44 + 20 * n
        tag, offset, packed, unpacked, checksum = struct.unpack_from(">4sLLLL", data, place)
        if tag == b"zzzz":
            struct.pack_into(">4sLLLL", data, place, tag, offset, packed - 10, unpacked, checksum)
    return bytes(data)


def test_a_woff_table_with_a_cut_zlib_stream_is_not_a_font():
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(woff_with_cut_stream(), "cut.woff")


# Every way in refuses a bomb with a clear message


def bomb():
    return woff2(8 * MB, 100_000)


def big():
    return woff2(10, 2 * MB)


def admin_post(client, django_user_model, data):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    return client.post(
        reverse("admin:capy_theme_font_add"),
        {
            "family": "Bomb Sans",
            "source": "upload",
            "files-TOTAL_FORMS": "1",
            "files-INITIAL_FORMS": "0",
            "files-MIN_NUM_FORMS": "0",
            "files-MAX_NUM_FORMS": "1000",
            "files-0-subset": "all",
            "files-0-file": SimpleUploadedFile("bomb.woff2", data, "font/woff2"),
        },
    )


@pytest.mark.parametrize(
    "make, message",
    [(bomb, "unpacks to more than it says"), (big, "too big once unpacked")],
)
def test_the_admin_upload_refuses_a_bomb_with_a_clear_message(
    client, django_user_model, make, message
):
    response = admin_post(client, django_user_model, make())
    assert response.status_code == 200
    assert message in response.content.decode()
    assert not Font.objects.filter(family="Bomb Sans").exists()


def export_with_font(data):
    manifest = {
        "format": "capy-theme-export/1",
        "theme": {
            "name": "T",
            "slug": "t",
            "base": "light",
            "settings": {},
            "font_roles": {"body": "font-1"},
        },
        "fonts": {
            "font-1": {
                "family": "Bomb Sans",
                "source": "upload",
                "files": [{"path": "fonts/1-0.woff2", "weight": 400, "style": "normal"}],
            }
        },
        "images": {},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("theme.json", json.dumps(manifest))
        archive.writestr("fonts/1-0.woff2", data)
    buffer.seek(0)
    return buffer


@pytest.mark.django_db
def test_the_export_is_valid_with_a_real_font():
    theme = import_theme(export_with_font(small("woff2")))
    assert Font.objects.filter(family="Bomb Sans").exists() and theme.pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    "make, message",
    [(bomb, "unpacks to more than it says"), (big, "too big once unpacked")],
)
def test_a_theme_import_refuses_a_bomb_and_keeps_nothing(make, message, tmp_path):
    with pytest.raises(ValidationError, match=message):
        import_theme(export_with_font(make()))
    assert not Theme.objects.exists()
    assert not Font.objects.filter(family="Bomb Sans").exists()
    assert not FontFile.objects.exists()
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]


class BombGoogle(FakeGoogle):
    """Google answers normally, but the font files it serves are bombs."""

    def __init__(self, file):
        super().__init__()
        self.file = file

    def __call__(self, url, timeout=60):
        if url.startswith("https://fonts.gstatic.com/"):
            self.requests.append(url)
            return self.file
        return super().__call__(url, timeout)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "make, message",
    [(bomb, "unpacks to more than it says"), (big, "too big once unpacked")],
)
def test_a_google_font_that_is_a_bomb_is_refused_and_nothing_is_kept(make, message):
    with pytest.raises(ValidationError, match=message):
        import_family("Lora", download=BombGoogle(make()))
    assert not Font.objects.filter(family="Lora").exists()
    assert not FontFile.objects.exists()


@pytest.mark.django_db
def test_the_admin_google_import_shows_the_bomb_message(client, django_user_model, monkeypatch):
    monkeypatch.setattr(
        "capy_theme.admin.fonts.import_family",
        lambda family, **kw: import_family(family, download=BombGoogle(bomb()), **kw),
    )
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    response = client.post(
        reverse("admin:capy_theme_font_import_google"),
        {"family": "Lora", "weights": ["400"], "subsets": ["latin"]},
    )
    assert response.status_code == 200
    assert "unpacks to more than it says" in response.content.decode()
    assert not Font.objects.filter(family="Lora").exists()


class HalfBombGoogle(FakeGoogle):
    """The Latin files are real fonts; the Cyrillic ones are bombs."""

    def __call__(self, url, timeout=60):
        if url.startswith("https://fonts.gstatic.com/") and "/cyr-" in url:
            self.requests.append(url)
            return bomb()
        return super().__call__(url, timeout)


@pytest.mark.django_db
def test_a_google_import_refused_halfway_leaves_no_files_behind(tmp_path):
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        import_family("Lora", subsets=("latin", "cyrillic"), download=HalfBombGoogle())
    assert not Font.objects.filter(family="Lora").exists()
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]


def test_a_woff2_with_a_bad_flavor_is_not_a_font():
    data = bytearray(small("woff2"))
    data[4:8] = b"\xff\x00\x01\x00"  # the sfnt version WOFF2 stores; fontTools checks it late
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(bytes(data), "bad.woff2")


@pytest.mark.django_db
def test_the_admin_shows_not_a_font_for_a_cut_zlib_stream(client, django_user_model):
    response = admin_post(client, django_user_model, woff_with_cut_stream())
    assert response.status_code == 200
    assert "isn&#x27;t a font" in response.content.decode()
