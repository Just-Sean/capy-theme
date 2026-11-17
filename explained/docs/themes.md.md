# docs/themes.md

**Covers:** themes as a whole and how they go live.

- the settings schema (every theme's settings are validated against a JSON Schema)
- the theme's admin page, section by section
- branding
- **drafts and publishing:** the theme page's Save and publish area (Save draft, Save and publish, Save, publish and activate), the theme list's Publish and Activate buttons, revisions, compare, restore
- the default theme (activated with those buttons), the list's "Showing now" column (the theme showing right now on every domain without a site theme of its own), scheduled themes and multiple sites (a theme per domain)
- the visitor theme picker
- light and dark mode
- the three extra permissions (`publish_theme`, `edit_custom_css`, `import_theme`)
- export and import, including the command-line commands (`theme_export`, `theme_import`, `theme_publish`, `theme_rebuild_images`)

**Code it describes:** `src/capy_theme/themes/`, `admin/`, `portability/`.
