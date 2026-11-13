"""A fake Google Fonts API for tests: no network."""

import io
import urllib.error
import urllib.parse

from fontTools.ttLib import TTFont

from tests.support.fonts import ttf_bytes


def woff2():
    font = TTFont(io.BytesIO(ttf_bytes()))
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def face(subset, style, weight, name):
    return f"""/* {subset} */
@font-face {{
  font-family: 'Lora';
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/lora/v37/{name}.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}}
"""


class FakeGoogle:
    """Answers like the Google Fonts API for a family with 400, 700 and 400 italic."""

    def __init__(self, family="Lora", have=((0, 400), (0, 700), (1, 400))):
        self.family, self.have, self.requests = family, set(have), []

    def __call__(self, url, timeout=60):
        self.requests.append(url)
        if url.startswith("https://fonts.gstatic.com/"):
            return woff2()
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["family"][0]
        name, _, axes = query.partition(":ital,wght@")
        combos = {tuple(int(x) for x in c.split(",")) for c in axes.split(";")}
        if name != self.family or not combos <= self.have:
            raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)
        css = ""
        for italic, weight in sorted(combos):
            style = "italic" if italic else "normal"
            css += face("latin", style, weight, f"lat-{style}")  # variable: one file per style
            css += face("cyrillic", style, weight, f"cyr-{style}")
        return css.encode()
