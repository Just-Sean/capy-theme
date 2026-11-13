# src/capy_theme/images/

**Everything about a theme's images:** uploading safely, logos, the icon and favicons, the sharing image and backgrounds.

Each image goes in a **slot**:

- six logos: main, stacked, mark, wordmark, email, print
- the icon
- the social sharing image
- the login background and the background pattern

Each slot has light and dark versions. Uploading never changes what visitors see. An image is used only once it's chosen for its slot and the theme is published. Uploaded files are never changed, so older revisions keep theirs.

| File | Job |
| --- | --- |
| `slots.py` + `slots.json` | The slots, their size limits and which can't be SVG |
| `models.py` | `ThemeAsset` (an upload) and `ThemeAssetVariant` (a generated copy) |
| `uploads.py` | Checking and cleaning an upload, storing it |
| `gif_frames.py` | Reading a GIF's frame structure without decoding pixels |
| `svg.py` + `svg_allowlist.json` | Sanitizing SVGs |
| `logos.py` | Logo slots, fallbacks, copying chosen images into revisions |
| `variants.py` | Smaller copies of header logos (AVIF, WebP, PNG/JPEG) |
| `logo_tag.py` | The HTML and CSS for `{% theme_logo %}` |
| `icons.py` + `icons.json` | Every favicon and app icon from one square image |
| `sharing.py` | The 1200 × 630 sharing image |
