# src/capy_theme/static/capy_theme/editor/controls/image-sections.js

**What it is:** the editor's image sections, named like the admin's (#271):

- **Logos:** the main logo (light and dark), the header logo heights (desktop and phone), and a folded **More logo versions (optional)** with the stacked, mark, wordmark, email and print logos. Email and print have no dark choice.
- **Icon:** the icon (light and dark), its background color and padding, and a rough preview of how they look. The real icons are made when publishing; the browser tab shows the draft icon meanwhile.
- **Backgrounds:** the login background and the page background pattern.
- **Sharing image:** light only.

Each slot is a `ui.slotControl` (`image-slot.js`). Everything is saved with Save draft.
