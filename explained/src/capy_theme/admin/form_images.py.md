# src/capy_theme/admin/form_images.py

**What it is:** the form's images (#271). Each image is uploaded and chosen where it's used.

- **Per slot and mode, one field** (`slot_image.py`): the current image, a choice of this slot's earlier uploads, a new upload and the alt text. This covers the six logos, the icon, the sharing image and both backgrounds. The modes come from `slots.json`, so the email and print logos and the sharing image have no dark choice. Help and empty text come from `images/slot_text.py`.
- **Header logo heights:** desktop and phone.
- **The icon's background color and padding.**
- **`ask_to_choose_again(form)`:** browsers don't keep a chosen file when the page comes back with errors, so each slot that had a new file says to choose it again. `ThemeAdmin` calls it whenever the page is shown again after a failed save, so errors in the Media list or from the model's own checks (e.g. a name that's taken) count too.
- **`save_images(form, theme)`:** runs after the theme is saved. It stores each new upload with its own alt text and chooses it for its slot (a new upload wins over the choice in the list), and saves alt text edited for the image the page showed (`alt_for`), never another one.

Choosing or uploading an image only changes the draft. It's used once published.
