# src/capy_theme/admin/inlines.py

**What it is:** the two lists inside the theme edit page.

- **`ThemeAssetInline`:** **Media**, every image uploaded for the theme (#271). Images are uploaded and chosen where they're used (Logos, Icon, Backgrounds, Sharing image), so there's no upload form here. Each row shows:
  - a preview, the slot and mode
  - the details (file name, size, type)
  - **Used as:** where it's used in the draft, the published theme or an earlier revision, or "Not used: can be deleted" (the revisions are read once per page)
  - the alt text, which can be edited

  Unused images can be deleted. Editing and deleting need the change-theme permission. The image file itself never changes, so older revisions keep theirs.
- **`ThemeAssetFormSet`:** refuses to delete an image that's in use (`images/assets.refusal`). It checks in `_should_delete_form`, where Django decides which rows are deleted, so the refusal counts as a normal row error: the save fails, the page says so at the top, the Media list is shown unfolded and the row's Delete box is unticked. The row says where the image is used and what to do (choose another image or None, or Same as light for dark, and save; then publish if the published theme uses it). An image an earlier revision uses can't be deleted, because restoring that revision needs it.
- **`ThemeRevisionInline`:** the **published revisions**, read-only (no add, change or delete), marking the live one.
