# Fonts

Code: `src/capy_theme/fonts/` (library and stacks, uploads, Google Fonts import, the curated list) and the `capy_theme_add_fonts` command.

## Fonts

Fonts live in a shared **font library** (admin → Capy Theme → **Fonts**): each
font has a family name, a source, a fallback stack and a license note, and its
WOFF2 files (one per weight and style, optionally per character subset). Any
theme can use any font.

A theme chooses fonts for four roles, in the **Fonts** section of its admin page
or in the live editor:

| Role | Applies to | CSS |
| --- | --- | --- |
| Body text | the page's text | `--font-sans` (Tailwind's default) and `body` |
| Headings | `h1`–`h6` | `--capy-font-heading` |
| Monospace | `code`, `kbd`, `samp`, `pre` | `--font-mono` |
| Display | elements with the `capy-display` class | `--capy-font-display` |

Roles left on "Default" use the project's own fonts.

**System font stacks** are in the library from the start (added by a migration):
System sans, System serif and System mono, plus ten styles from
[Modern Font Stacks](https://modernfontstacks.com) (CC0): Transitional, Old Style,
Humanist, Geometric Humanist, Neo-Grotesque, Rounded, Slab Serif, Didone,
Monospace Code and Industrial. They use fonts already on the visitor's device,
so **nothing is downloaded**. They're the fastest option.

**Uploading fonts.** On a font's admin page, add files under **Files**: WOFF2,
WOFF, TTF or OTF. Each file is checked with fontTools (anything that isn't a font,
like a renamed image, is refused), converted to WOFF2, and by default trimmed to
the **Latin** characters, which often cuts it to a few percent of its size. Choose
another subset (Latin Extended, Cyrillic, Greek, Vietnamese) or **All characters**
to keep everything. Leave weight and style blank to read them from the font. The
size limit is 5 MB per file (`CAPY_THEME_FONT_MAX_BYTES`).

**Importing from Google Fonts.** On the Fonts list in the admin, click **Import
from Google Fonts**, type a family name (e.g. *Lora*), and pick the weights,
italics and character sets. The server downloads the files **once** and stores
them with your other media, so pages load the font **from your own site**:
visitors' browsers never contact Google. Weights a family doesn't have are skipped.

**External font stylesheets** are for licensed fonts that can't be self-hosted,
like **Adobe Fonts**. Add a font with source **External stylesheet**, the font's
CSS family name as the family (e.g. `proxima-nova`), and the provider's https
stylesheet address (e.g. your Adobe Fonts kit, `https://use.typekit.net/abc1234.css`).
`{% theme_head %}` then links that stylesheet before the theme's own, and the live
editor links it while previewing. The provider's stylesheet defines the font
faces, so the browser loads them from the provider.

If the project uses a **Content Security Policy**, allow the provider's domains:
the stylesheet's domain in `style-src` and the font files' domain in `font-src`.
For Adobe Fonts, with Django 6.1's built-in CSP setting:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "style-src": [CSP.SELF, "https://use.typekit.net", "https://p.typekit.net"],
    "font-src": [CSP.SELF, "https://use.typekit.net"],
    # ...the project's other directives
}
```

(Self-hosted fonts, which means uploaded, imported, bundled and system ones,
need no extra CSP entries.)

**A curated collection of 30 open-license fonts** is bundled with the module
(Inter, Roboto, Open Sans, Lato, Montserrat, Source Sans 3, Nunito, Poppins, Work
Sans, IBM Plex Sans, DM Sans, Raleway, Figtree, Manrope, Outfit, Merriweather,
Lora, Playfair Display, Source Serif 4, Libre Baskerville, EB Garamond, Crimson
Pro, PT Serif, IBM Plex Serif, JetBrains Mono, Fira Code, Source Code Pro, IBM
Plex Mono, Oswald and Bebas Neue). Add them to the library with:

```bash
uv run python manage.py capy_theme_add_fonts     # in the demo: uv run python demo/manage.py capy_theme_add_fonts
```

It copies each font's files (Latin regular, bold and italic, where the font has
them) into the project's media storage and adds them to the library. Fonts already
there are skipped, so it's safe to run again. The font list in the admin shows a
preview of each font, and the editor shows a sample under each font choice.

All 30 are under the SIL Open Font License 1.1. Their license files are in
`src/capy_theme/static/capy_theme/fonts/<font>/LICENSE`. They come from
[Fontsource](https://fontsource.org). To change the collection, edit the list in
`scripts/fetch_curated_fonts.py` and run:

```bash
uv run python scripts/fetch_curated_fonts.py
``` The stylesheet adds an
`@font-face` rule (with `font-display: swap`) for each file. The element rules
are in `@layer base`, so a project's own utility classes, like `font-serif`, still
win. When a theme is published, its fonts' details and file URLs are copied into
the revision, so editing the library later can't change a published theme.
