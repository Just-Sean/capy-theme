# src/capy_theme/templates/capy_theme/widgets/slot_image.html

**What it is:** one image slot and mode on the theme edit page (`admin/slot_image.py`, #271):

- **the current image:** a preview with its size in px and file size, or the slot's empty text (e.g. "No image: the main logo is used.")
- **the choice:** a dropdown of this slot's earlier uploads. The field's own label (e.g. "Main logo (light)") is for it.
- **Upload a new image:** a file input, limited to the file types the slot takes
- **Alt text:** a text box, at most 200 characters

Each input has its own label. No inline styles: the look is in `static/capy_theme/admin/images.css`.
