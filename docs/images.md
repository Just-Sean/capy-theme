# Images, logos and icons

Code: `src/capy_theme/images/` (uploads, SVG cleaning, logo slots and copies, icons, the sharing image). capy-theme makes these available; it only applies the logo tag and the tab icons to pages.

## Images

A theme's images (logos, the icon, the social sharing image, backgrounds) are
uploaded and chosen **where they're used**: on the theme's admin page under
**Branding** (Logos, More logo versions, Icon, Backgrounds, Sharing image), and in
the live editor's sections of the same names. Each slot, for light or dark mode,
shows:

- what it's for and its limits (size, largest width or height, whether SVG is
  allowed), and what happens if it's left empty;
- its current image, and a choice of the images uploaded for it earlier;
- **Upload a new image**, with its alt text. In the admin, the new image is
  stored and chosen when you save the page (several slots can get one in the same
  save; if another part of the page has an error, choose the file again, since
  browsers don't keep it). In the live editor it's stored straight away and
  chosen in your unsaved changes: **Save draft** keeps the choice, **Revert**
  drops it (the image stays in the theme's list);
- the alt text of the current image, which can be changed at any time.

An image stays with the slot it was uploaded for. For every upload:

- The type is worked out from the file's content, not its name. Only PNG, JPEG,
  WebP, GIF and SVG are accepted, so a text file renamed `.png` is rejected.
- Each slot has a size limit and a maximum width and height (in
  `src/capy_theme/images/slots.json`): 1 MB for the email logo, 2 MB for the
  other logos, the icon and the background pattern, and 5 MB for the print logo,
  social image and login background. A project can set a lower cap for every
  slot with `CAPY_THEME_IMAGE_MAX_BYTES`.
- Animated images (GIFs, and animated WebP or PNG) can be at most 2000 pixels
  wide or high, have at most 500 frames, and at most 50 million pixels in all
  (frames × width × height): about 150 MB of memory and a second of work at most.
  A frame that changes a few pixels takes only a few bytes in the file but is
  decoded at full size, so without these limits a small file could use huge
  amounts of memory and time when it's saved again. They're checked before
  anything is decoded. A project can change them with
  `CAPY_THEME_ANIMATION_MAX_SIZE`, `CAPY_THEME_ANIMATION_MAX_FRAMES` and
  `CAPY_THEME_ANIMATION_MAX_PIXELS`.
- For GIFs, every frame's own position and size is read from the file first. A
  GIF whose frames reach past its edges is refused (GIF tools don't make them,
  and Pillow would grow the image while decoding, after the checks).
- A damaged file is refused as "not a supported image". Anything else that goes
  wrong while processing an image (e.g. the server running out of memory) is
  left as a normal server error, so Django logs it and it gets noticed.
- The image is saved again without EXIF, text chunks and comments, so camera
  details and GPS locations are removed. Photos are turned upright first.
  Color profiles are kept. Animated GIFs keep every frame, their timing,
  looping and transparency, and how each frame is cleared before the next. (A
  rare GIF that mixes "leave in place" and "clear to the background" between
  frames can still look slightly different: a limitation of Pillow, which saves
  the cleaned copy. GIF tools normally use one setting for every frame.)
- SVGs are cleaned with a strict allow-list (`src/capy_theme/images/svg_allowlist.json`, used by `images/svg.py`): only
  drawing elements and attributes are kept. Scripts, event handlers (`onload`
  and so on), embedded HTML, animation, links to other files or sites, and CSS
  `@import` or external `url()` are removed. SVGs must be UTF-8, and SVGs with a
  DOCTYPE or entities are rejected. They're parsed with `defusedxml`, which also
  refuses entities and external references itself, as a second layer.
- SVGs aren't converted to PNG. The slots where SVG can't be used take a PNG,
  JPEG, WebP or GIF instead: the email logo (email programs don't show SVG), the
  social sharing image (social sites don't accept it) and the icon (favicons are
  made from it). They're listed under `no_svg` in `src/capy_theme/images/slots.json`.

Files are stored under `MEDIA_ROOT/capy_theme/assets/<slot>/`. The image itself
is never changed after upload (only its alt text can be): a new image is a new
asset, so older revisions keep theirs. Uploading doesn't change what visitors
see: an image is only used once it's chosen for its slot and the theme is
published. The live editor shows the draft's logos and tab icon on the page
straight away, in your browser only (see [the editor](editor.md)).

### Media

The admin's **Media** tab lists every image uploaded for the theme, with a
preview, its slot and mode, its size, where it's used, and its alt text (which can
be changed there too). An image nothing uses can be deleted. An image that the
draft or the published theme uses can't: the save is refused with a message
saying where it's used. Upload a new image for that slot, or set the slot to
None, and save; then delete it. (Unsetting it and deleting it in the same save
works too.) Managing images needs the same permission as editing the theme.

## Logos

There are six logo slots. Most sites only need the **main** logo: it's shown up
front under **Logos**, and the other five are folded away under **More logo
versions (optional)**, each saying what it's for:

| Slot | What it's for |
| --- | --- |
| **Main** | The site header. The one capy-theme itself shows; every other slot uses it when empty. |
| **Stacked** | Symbol above the name, for narrow spaces (a phone-width header, a sidebar). |
| **Mark** | The symbol alone, for tight spots (an app bar, an avatar, a footer). |
| **Wordmark** | The name alone, in lettering, without the symbol. |
| **Email** | HTML emails. PNG or JPEG (email programs don't show SVG); light only. |
| **Print** | High resolution, for printed pages, PDFs or invoices; light only. |

The project's templates use the other five with `{% theme_logo slot="mark" %}` and
so on, or through [theme artifacts](artifacts.md). To set one:

1. In the slot (admin: **Branding → Logos** or **More logo versions**; live
   editor: **Logos**), upload a new image, or pick an earlier one.
2. Save (admin) or **Save draft** (live editor), then publish.

Fallbacks: dark mode uses the slot's light image if there's no dark one, and a
slot with no image uses the main logo. Email and print logos only have a light
image (emails and print have no dark mode).

`{% theme_logo slot="main" %}` (the default) outputs the logo for that slot:

- **Header slots** (main, stacked, mark, wordmark) give a `<picture>` with AVIF
  and WebP sources and a PNG or JPEG fallback. On upload, smaller copies are made
  at widths from 64 to 1280 px (and the image's own width, up to 2560), stored
  under `MEDIA_ROOT/capy_theme/assets/<slot>/variants/`. The `sizes` attribute
  comes from the header heights, so phones download a smaller file. SVG logos
  are used as they are.
- **Header heights**: the **Header logo height** (default 40 px) and **on
  phones** (default 32 px, for windows up to 640 px wide) are set in the same
  Logos section. The theme's stylesheet sizes `img.capy-logo` with them; a
  utility class on the tag (e.g. `class="h-12"`) still wins.
- **Light and dark**: if the slot has a dark image, both are output and the
  theme's stylesheet shows the one for the current mode (it follows the toggle
  and the device setting). Both are `loading="lazy"`, so only the one shown is
  downloaded.
- **Email and print** slots give a plain `<img>` of the light image (email
  programs don't handle `<picture>` or the light/dark CSS).

Alt text comes from the image's alt text, then the theme's logo alt text, then
the site name.

## Icon and favicons

Every browser and home-screen icon is made from one square image (at least
512 × 512 px is best; SVG isn't accepted here). To set it:

1. In the **Icon** section (admin: **Branding → Icon**; live editor: **Icon**),
   upload the image or pick an earlier one, optionally with a dark version, and
   set the **Icon background** (a hex color; blank is transparent) and **Icon
   padding** (0–25% on each side) if you want. The live editor shows a preview of
   them, and the browser tab shows the draft's icon while the editor is open.
2. Save and publish. The icons are made when you publish.

The files are saved in `MEDIA_ROOT/capy_theme/icons/<id>/`, where the id comes
from the icon image and its settings, so each revision keeps its icons:

| File | Used for |
| --- | --- |
| `favicon.ico` | Browser tab (16, 32 and 48 px in one file) |
| `favicon.svg` | Browser tab; switches to the dark icon in dark mode |
| `apple-touch-icon.png` | iPhone and iPad home screen (180 px, never transparent: white if no background is set) |
| `icon-192.png`, `icon-512.png` | Android home screen and app icons |
| `icon-maskable-512.png` | Android adaptive icons: the icon sits in the middle 80%, on a solid background |
| `icon-monochrome-512.png` | Single-color icons: white in the icon's shape |

`{% theme_head %}` links the ICO, SVG, 192 px and Apple icons (the tab and
home-screen icon are part of the site's look). The 512 px, maskable and
monochrome icons are for a web app manifest, which capy-theme doesn't serve: a
project or PWA module gets them from [theme artifacts](artifacts.md).

## Sharing image

Upload or pick an image (PNG or JPEG, not SVG) in the **Sharing image** section
(admin: **Branding → Sharing image**; live editor: **Sharing image**), then
publish. It's cropped
from its center to 1200 × 630 when uploaded (transparent parts become white).
capy-theme doesn't output link-preview tags (Open Graph, Twitter cards): the
project or another module adds them, using the image from
[theme artifacts](artifacts.md).

## Background images

Two optional decorative images, each with a light and dark version: a **login
background** and a **page background pattern** (SVG allowed). Upload or pick them
in the **Backgrounds** section (admin: **Branding → Backgrounds**; live editor:
**Backgrounds**, where they preview straight away), then publish. They show only where the project's templates
use them:

- **Classes**: `class="capy-bg-login"` (covers the element, centered) or
  `class="capy-bg-pattern"` (repeats). The demo's `<body>` uses `capy-bg-pattern`.
- **CSS variables**: `--capy-bg-login` and `--capy-bg-pattern` (each a `url(...)`,
  switching with light and dark mode), e.g.
  `background-image: var(--capy-bg-login);` in the project's CSS.
- **Template values**: `{{ theme.background_login_url }}` and
  `{{ theme.background_pattern_url }}` (the light versions; `""` if not set).

Dark mode uses the light image if there's no dark one.
