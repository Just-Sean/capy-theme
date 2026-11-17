# src/capy_theme/admin/inlines.py

**What it is:** the two lists inside the theme edit page.

- **`ThemeAssetInline`:** **Media**, every image uploaded for the theme (#271). Images are uploaded and chosen where they're used (Logos, Icon, Backgrounds, Sharing image), so there's no upload form here. Each row shows:
  - a preview, the slot and mode
  - the details (file name, size, type)
  - **Used as:** where it's used in the draft or the published theme, how many earlier revisions use it, or "Not used: can be deleted" (the revisions are read once per page)
  - the alt text, which can be edited

  Unused images can be deleted. Editing and deleting need the change-theme permission. The image file itself never changes, so older revisions keep theirs.
- **`ThemeAssetFormSet`:** refuses a row's alt text edit when the same image's alt text was also changed, differently, in its slot in the same save (the form leaves its edits on the unsaved theme as `capy_alt_edits`); and refuses to delete an image that's in use (`images/assets.refusal`). It checks in `_should_delete_form`, where Django decides which rows are deleted, so the refusal counts as a normal row error: the save fails, the page says so at the top, the Media list is shown unfolded and the row's Delete box is unticked. The row says where the image is used and what to do: if only the draft uses it, choose another image or None (Same as light for dark) and save, then delete it; once it has been published it can't be deleted, because restoring a published version needs it.
- **`ThemeRevisionInline`:** the **published revisions**, read-only (no add, change or delete), marking the live one.
