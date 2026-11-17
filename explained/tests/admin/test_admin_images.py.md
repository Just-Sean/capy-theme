# tests/admin/test_admin_images.py

**What it tests:** the theme page's images (#271): uploaded and chosen where they're used, with editable alt text, and a Media list to manage them.

**Code it covers:** `src/capy_theme/admin/form_images.py`, `admin/slot_image.py`, `admin/inlines.py`, `images/assets.py`, `widgets/slot_image.html`

**Its 15 tests** (each name says what must hold):

- every slot explains what its for and its limits
- the main logo is up front and the others are under more
- a slot shows its current image and offers its earlier uploads
- an svg cant be picked where it isnt allowed
- choosing an earlier upload and editing its alt text
- several uploads in one save
- a file must be chosen again if another field has an error
- new themes can have images from the start
- media lists each image with where its used
- an unused image can be deleted
- an image in use cant be deleted
- unsetting an image and deleting it in one save works
- alt text can be edited in media
- media has no upload form
- where used counts the draft and the live revision

Run just this file with `uv run pytest tests/admin/test_admin_images.py`.
