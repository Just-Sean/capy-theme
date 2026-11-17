# tests/editor/test_editor_images.py

**What it tests:** the live editor's images (#271): slots described like the admin, uploads chosen where they're used, editable alt text, and the draft's logos and icon shown on the page before publishing.

**Code it covers:** `src/capy_theme/editor/` (`state.py`, `saving.py`, `preview.py`, `page_images.py`, `live_edit_view.py`), `{% theme_logo %}`, and the editor's image scripts

**Its 16 tests** (each name says what must hold):

- every slot is described like in the admin
- alt text is saved with the draft
- bad alt text is refused and nothing is saved (an unknown image, another theme's image, not an object, not text, too long)
- the preview has the drafts logos with fallbacks and the icon
- without a logo the preview says so
- logos are marked for editors so the preview can find them
- visitors get the same logo html as before
- editors get a hidden marker where there is no logo yet
- the live edit page header shows the theme being edited
- without a logo the header shows the site name ready for a preview
- the editor loads the new image scripts and not the old ones
- the upload button cant send twice
- closing the editor puts the published logos and icon back
- the page preview only reads its own attribute as json
- the draft reaches the page on load preview and revert
- alt text edits count as unsaved changes

The scripts can't run here, since the project has no browser test setup: the script tests only check their source.

Run just this file with `uv run pytest tests/editor/test_editor_images.py`.
