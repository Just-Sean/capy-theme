# tests/admin/test_admin_images.py

**What it tests:** the theme page's images (#271): uploaded and chosen where they're used, with editable alt text, and a Media list to manage them.

**Code it covers:** `src/capy_theme/admin/form_images.py`, `admin/slot_image.py`, `admin/inlines.py`, `images/assets.py`, `widgets/slot_image.html`

**Its 62 tests** (each name says what must hold):

- every slot explains what its for and its limits
- the main logo is up front and the others are under more
- a slot shows its current image and offers its earlier uploads
- an svg cant be picked where it isnt allowed
- choosing an earlier upload and editing its alt text
- a new upload gets its own alt text not the current images
- a forged alt for another slots image is ignored
- choose again is said when the theme name is taken
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
- choosing another earlier image keeps its own alt text
- choosing an earlier image for an empty slot keeps its alt text
- a file must be chosen again when media has an error
- a choice that isnt this slots is refused
- a dark upload can be chosen for light
- an svg is refused in a slot without svg
- an svg is fine in the main logo
- an oversized file is refused before it is read
- a bad upload isnt told to choose again
- an upload wins over choosing an earlier image
- uploads in different sections in one save
- email and print dark fields posted anyway are ignored
- alt text is trimmed and limited
- an alt text edit in media isnt undone by the slot
- an image only the live revision uses cant be deleted
- deleting two where one is in use deletes neither
- an image used in another slot mode cant be deleted
- a user without change theme cant delete from media
- an image an earlier revision uses cant be deleted
- the advice never sends people in a circle
- many revisions are counted not listed
- an old dark email choice doesnt block deleting
- editing the light alt isnt undone by the dark box showing the same image
- editing the dark alt of an image also shown for light
- two different alt edits for the same image arent silently dropped
- changing the choice and editing the alt applies to the image shown
- an upload and an alt edit of the current image both apply
- garbage alt for is ignored without an error
- alt for an image deleted in media in the same save
- the add page ignores alt fields
- a typed alt is kept when the page comes back with errors
- choose again on the add page
- choose again is said for every upload when media has an error
- choose again isnt said for a slot without an upload
- choose again with a bad media alt text
- after a refused delete saving the page again works
- two deletes one refused then the other alone works
- an image only a dark revision choice uses cant be deleted
- the refusal names draft live and older revision together
- revisions of an unsaved theme and a theme without revisions
- where used survives older revision snapshots
- a legacy revision logo file isnt counted as in use
- a legacy dark email choice in draft and live doesnt block delete
- a light only slots label has no mode

Run just this file with `uv run pytest tests/admin/test_admin_images.py`.
