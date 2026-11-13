# src/capy_theme/admin/import_export.py

**What it is:**

- **Export** (a button on the theme page): downloads `<slug>.capy-theme.zip` (`export_theme`).
- **Import theme** (a button on the theme list, needs `import_theme`): an upload page. It runs `import_theme`, keeping custom CSS only if the user may edit it. It shows errors clearly, then opens the new draft.
