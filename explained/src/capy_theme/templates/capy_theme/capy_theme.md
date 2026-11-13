# src/capy_theme/templates/capy_theme/

| Item | For |
| --- | --- |
| `mode_toggle.html` | `{% theme_mode_toggle %}` |
| `theme_picker.html` | `{% theme_picker %}` |
| `admin/` | The admin pages capy-theme adds or extends |
| `editor/` | The live editor's loader and the Components view |
| `widgets/` | The admin's color input |

Visitor-facing templates use daisyUI classes, so they match the project's look. The editor's panel is built by JavaScript, not templates.
