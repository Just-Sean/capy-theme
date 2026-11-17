# src/capy_theme/admin/inlines.py

**What it is:** the two lists inside the theme edit page.

- **`ThemeAssetInline`:** **Media**, every image uploaded for the theme (#271). Images are uploaded and chosen where they're used (Logos, Icon, Backgrounds, Sharing image), so there's no upload form here. Each row shows:
  - a preview, the slot and mode
  - the details (file name, size, type)
  - **Used as:** where it's used in the draft or the published theme, or "Not used: can be deleted"
  - the alt text, which can be edited

  Unused images can be deleted. Editing and deleting need the change-theme permission. The image file itself never changes, so older revisions keep theirs.
- **`ThemeAssetFormSet`:** refuses to delete an image that's in use (`images/assets.where_used`). The row stays and says where it's used, and how to free it: upload a new image for that slot or set it to None, save, then delete.
- **`ThemeRevisionInline`:** the **published revisions**, read-only (no add, change or delete), marking the live one.
