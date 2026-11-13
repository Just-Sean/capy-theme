# src/capy_theme/images/sharing.py

**What it is:** the **sharing image**, the picture shown when a link to the site is shared (Facebook, LinkedIn, X, chat apps).

- **`make_sharing_image(asset)`:** when uploaded to the `social` slot, the image is cropped from its center to **1200 × 630**. Transparent parts become white, since some sites show transparency as black. It's saved as a variant.
- **`sharing_image(snapshot)`:** the published one's file, size and alt text.

capy-theme only makes the image. The `<meta property="og:image">` tags belong to the project or another module, which gets the image from artifacts.
