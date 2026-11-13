# src/capy_theme/editor/views.py

**What it is:** the editor's JSON endpoints. Each one checks permission first (403 if not allowed) and sends `Cache-Control: no-store` where the data is private.

| View | URL | Does |
| --- | --- | --- |
| `editor_state` | `editor/<id>/state/` (the editor uses GET; the view doesn't restrict the method) | The draft and controls |
| `editor_preview` | `POST editor/<id>/preview/` | CSS and values for unsaved changes; writes nothing |
| `editor_suggestions` | `POST editor/<id>/suggestions/` | Color suggestions |
| `editor_save` | `POST editor/<id>/save/` | Save draft, return the new state |
| `editor_publish` | `POST editor/<id>/publish/` | Publish (needs `publish_theme`), with an optional note |
| `editor_upload` | `POST editor/<id>/upload/` | Upload an image through the same checks as the admin |
| `editor_visitor_view` | `GET editor/visitor-view/` | "See it as a visitor" data |

**Errors come back as JSON with clear messages:**

- 400: bad input or invalid values
- 409: nothing to publish, or someone else just published
