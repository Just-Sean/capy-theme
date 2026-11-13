"""Import a Google font into the library, so pages load it from this site.

The server asks the Google Fonts CSS API which WOFF2 files a family has, downloads
them once from fonts.gstatic.com, checks them, and stores them like uploads.
Visitors' browsers never contact Google.
"""

import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Font, FontFile
from .uploads import prepare

logger = logging.getLogger(__name__)

CSS_API = "https://fonts.googleapis.com/css2"
FILES_HOST = "https://fonts.gstatic.com/"
# The API picks the file format from the browser; this asks for WOFF2.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)
FAMILY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ]{0,99}$")
FACE = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", re.S)
WEIGHTS = [100, 200, 300, 400, 500, 600, 700, 800, 900]
SUBSETS = ["latin", "latin-ext", "cyrillic", "cyrillic-ext", "greek", "greek-ext", "vietnamese"]


def fetch(url, timeout=60):
    """Download an https URL and return its bytes (replaced in tests)."""
    if not url.startswith(("https://fonts.googleapis.com/", FILES_HOST)):
        raise ValueError(f"Refusing to download {url!r}: only Google Fonts addresses are allowed.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def css_url(family, combos):
    """The CSS API URL for a family and a list of (italic 0/1, weight) pairs."""
    axes = ";".join(f"{italic},{weight}" for italic, weight in sorted(combos))
    query = urllib.parse.urlencode({"family": f"{family}:ital,wght@{axes}", "display": "swap"})
    return f"{CSS_API}?{query}"


def parse(css):
    """Return one entry per @font-face in the API's CSS: subset, style, weight, url, range."""
    faces = []
    for subset, body in FACE.findall(css):
        rules = dict(re.findall(r"([\w-]+)\s*:\s*([^;]+);", body))
        url = re.search(r"url\((https://[^)]+)\)", rules.get("src", ""))
        if not url:
            continue
        faces.append(
            {
                "subset": subset,
                "style": rules.get("font-style", "normal").strip(),
                "weight": int(rules.get("font-weight", "400").strip().split()[0]),
                "url": url.group(1),
                "unicode_range": rules.get("unicode-range", "").strip(),
            }
        )
    return faces


def available_faces(family, combos, download=fetch):
    """Ask the API for the faces of `family`. Combinations the family lacks are skipped."""
    try:
        return parse(download(css_url(family, combos)).decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code != 400:
            raise
    # The API refuses the whole request if any one weight or style is missing,
    # so ask for each one on its own and keep those that exist.
    faces = []
    for combo in combos:
        try:
            faces += parse(download(css_url(family, [combo])).decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code != 400:
                raise
    return faces


def import_family(family, weights=(400, 700), italic=True, subsets=("latin",), download=fetch):
    """Download a Google font and add it to the library. Returns the new Font.

    Raises ValidationError if the name isn't valid, the font is already in the
    library, Google doesn't have it, or a downloaded file isn't a font.
    """
    family = " ".join(family.split())
    if not FAMILY_PATTERN.match(family):
        raise ValidationError("Enter a Google Fonts family name, e.g. Lora or Open Sans.")
    if Font.objects.filter(family__iexact=family).exists():
        raise ValidationError(f"“{family}” is already in the font library.")
    combos = [(0, w) for w in weights] + ([(1, w) for w in weights] if italic else [])
    try:
        faces = [f for f in available_faces(family, combos, download) if f["subset"] in subsets]
    except (urllib.error.URLError, TimeoutError) as error:
        logger.warning("Google Fonts couldn't be reached for %r: %s", family, error)
        raise ValidationError(f"Google Fonts couldn't be reached ({error}).") from error
    if not faces:
        raise ValidationError(
            f"Google Fonts has no “{family}” in the chosen weights and character sets. "
            "Check the name at fonts.google.com."
        )
    with transaction.atomic():
        font = Font.objects.create(
            family=family,
            source="google",
            license=f"Imported from Google Fonts. See https://fonts.google.com/specimen/"
            f"{family.replace(' ', '+')} for its license (most are the SIL Open Font License).",
        )
        stored = {}  # url -> saved file name (variable fonts reuse one file)
        for face in faces:
            if not face["url"].startswith(FILES_HOST):
                raise ValidationError("Google Fonts returned an unexpected file address.")
            name = stored.get(face["url"])
            if name is None:
                slug = family.lower().replace(" ", "-")
                prepared = prepare(download(face["url"]), f"{slug}-{face['subset']}.woff2", "all")
                holder = FontFile(font=font)
                holder.file.save(prepared["file"].name, prepared["file"], save=False)
                name = stored[face["url"]] = holder.file.name
            font_file = FontFile(
                font=font,
                weight=face["weight"],
                style=face["style"],
                subset=face["subset"],
                unicode_range=face["unicode_range"],
            )
            font_file.file.name = name
            font_file.save()
    logger.info("Imported Google font %r: %d font file(s) stored.", family, len(stored))
    return font
