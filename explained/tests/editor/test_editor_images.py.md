# tests/editor/test_editor_images.py

**What it tests:** the live editor's images (#271): slots described like the admin, uploads chosen where they're used, editable alt text, and the draft's logos and icon shown on the page before publishing.

**Code it covers:** `src/capy_theme/editor/` (`state.py`, `saving.py`, `preview.py`, `page_images.py`, `live_edit_view.py`), `{% theme_logo %}`, and the editor's image scripts

**Its 60 tests** (each name says what must hold):

- every slot is described like in the admin
- alt text is saved with the draft
- bad alt text is refused and nothing is saved
- the preview has the drafts logos with fallbacks and the icon
- without a logo the preview says so
- logos are marked for editors so the preview can find them
- visitors get the same logo html as before
- editors get a hidden marker where there is no logo yet
- the live edit page header shows the theme being edited
- without a logo the header shows the site name ready for a preview
- the editor loads the new image scripts and not the old ones
- the upload button cant send twice
- a late upload isnt chosen after the editor moved on
- a new upload is listed in every box for its slot
- closing cancels a preview on its way
- closing the editor puts the published logos and icon back
- the page preview only copies safe attributes
- the draft reaches the page on load preview and revert
- alt text edits count as unsaved changes
- odd alts are refused and nothing is saved
- alt text of exactly 200 after trimming is fine
- alt text can be cleared
- an alt edit doesnt change the published alt until publish
- alts need change theme
- a dark only slot uses its dark image and the main light
- email and print are light only in the preview
- the icon doesnt fall back to the logo
- a dark icon only
- the preview refuses another themes image
- the preview refuses an image from another slot
- an upload isnt chosen until save
- an upload to a bad slot or mode is refused
- a dark upload for a light only slot is refused
- alt text on upload is limited
- uploading needs change theme
- no marker for people who cant edit
- visitors with only a site name get no marker
- no request in the context means no marker
- editor html with a dark logo marks both pictures
- editor marker attrs are escaped
- the header escapes the drafts site name and tagline
- the header with no site name and no logo
- the header for a missing theme falls back
- save draft drops a dark choice for a light only slot
- the logo works without djangos auth middleware
- any attribute value works for editors
- valid uploads are still accepted
- an upload without a mode is light
- save drops a slot left with only a dark email choice
- save with only a dark email choice removes images
- an old dark email choice in the draft doesnt stop other edits
- odd images values are refused not crashing
- importing an export with an old dark email logo still works
- theme logo takes any attribute value for editors
- theme logo with a request whose user is none
- theme logo with no active theme and no user
- an odd mode gets add assets message
- a dark upload for a light only slot gets its own message
- an unknown slot with dark gets the slot message
- a repeated mode field uses the last value

The scripts can't run here, since the project has no browser test setup: the script tests only check their source.

Run just this file with `uv run pytest tests/editor/test_editor_images.py`.
