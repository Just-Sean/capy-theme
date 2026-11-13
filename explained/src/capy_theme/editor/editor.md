# src/capy_theme/editor/

**The server side of the live theme editor.** That's the panel staff open with "Edit theme" on any page, to change a theme's draft and see it on the real page straight away, in their browser only.

**How it fits together:**

1. `{% theme_head %}` calls `mount.py`. For staff who can edit, it adds the editor's script and settings to the page.
2. The script (`static/capy_theme/editor/`) loads the draft from `state/`, and sends every change to `preview/`, which returns CSS made by **the same code as publishing**.
3. **Save draft** and **Publish** call `save/` and `publish/`. Uploads go to `upload/`.
4. **See it as a visitor** uses `visitor-view/`. The **Components view** is its own page (`components/`) in an iframe.

Every endpoint requires staff with the change-theme permission (publishing also needs `publish_theme`), uses Django's CSRF protection for POSTs, and never caches.

| File | Job |
| --- | --- |
| `access.py` | Who can edit or publish; which theme the editor edits |
| `mount.py` | Adds the editor to a page |
| `state.py` | Everything the panel needs: the draft, the controls, the URLs |
| `preview.py` | Applies unsaved values and previews them (writes nothing) |
| `saving.py` | Save draft; color suggestions |
| `views.py` | The JSON endpoints |
| `visitors.py` | "See it as a visitor" |
| `components_view.py` | The Components view page and icon preview |
| `images_panel.py` | The Components view's images section |
| `custom_css_view.py` | The draft's custom CSS for the Components view |
