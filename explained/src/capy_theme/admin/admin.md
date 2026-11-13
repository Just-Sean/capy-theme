# src/capy_theme/admin/

**The Django admin pages:** Capy Theme → Themes, Fonts, Theme schedule, Site themes. The theme's admin page is the plain fallback to the live editor: everything can be edited here too.

The big theme form is split into one file per area (`form_*.py`). Each has three functions: `add_fields` (adds its fields to the form), `set_initial` (fills them from the theme) and `clean` (writes them back into the theme's settings). `theme_form.py` ties them together.

| File | Job |
| --- | --- |
| `__init__.py` | Imports the admin modules so they register |
| `theme_admin.py` | The theme list and edit page |
| `theme_form.py` | The theme edit form |
| `form_colors.py`, `form_type.py`, `form_shape.py`, `form_images.py`, `form_custom_css.py` | Each area's fields |
| `fieldsets.py` | The page's sections and their order |
| `inlines.py` | The images list and revisions list on the theme page |
| `publish_pages.py` | The Publish, Revisions (compare) and Restore pages |
| `import_export.py` | Export button and Import theme page |
| `fonts.py` | The font library admin and Google Fonts import |
| `schedule.py` | Theme schedule |
| `sites.py` | Site themes |
| `publish_permission.py` | Requires `publish_theme` for schedule and site pages |
