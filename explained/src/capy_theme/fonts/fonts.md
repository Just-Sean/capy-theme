# src/capy_theme/fonts/

**The font library:** fonts shared by all themes, and everything about getting fonts in and onto the page.

A theme picks a font for each of four **roles**: body, headings, monospace and display. Fonts come from five **sources**:

- **System stacks:** fonts already on the device, so nothing downloads.
- **Bundled:** 30 open-license fonts shipped with capy-theme.
- **Uploaded.**
- **Imported from Google Fonts:** stored locally.
- **External stylesheet:** for licensed fonts like Adobe Fonts.

| File | Job |
| --- | --- |
| `models.py` | `Font` and `FontFile` |
| `library.py` | Roles, fallback stacks, copying chosen fonts into revisions, preloads |
| `css.py` | The `@font-face` rules and role variables in the stylesheet |
| `uploads.py` + `subsets.json` | Checking, converting to WOFF2 and trimming font files |
| `google.py` | Importing a Google font |
| `curated.json` | The list of bundled fonts (for `capy_theme_add_fonts`) |
| `system_stacks.json` | The system font stacks |
