# src/capy_theme/images/logos.py

**What it is:** the logo slots and how a chosen image is found.

- **`LOGO_SLOTS`:** the six logos.
- **`HEADER_SLOTS`:** the four used in page headers, which get smaller copies.
- **`FALLBACK`:** an empty logo slot uses the main logo.
- **`HEIGHTS`:** the header logo height (40 px) and its height on phones (32 px). Phones means windows up to `MOBILE` = 640 px.
- **`snapshot_images(theme, settings)`:** the chosen images' file, size, type, alt text and variants, copied into a revision at publish time.
- **`resolve(snapshot, slot, mode)`:** the image a slot shows in a mode, following the fallbacks: dark falls back to light, then the slot falls back to the main logo. It also reads the single `logo` key that revisions published before logo slots used.
