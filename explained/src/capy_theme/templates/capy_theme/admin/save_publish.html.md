# src/capy_theme/templates/capy_theme/admin/save_publish.html

The theme page's **Save and publish** area at the bottom, in place of Django's own save buttons (#273). `theme_change_form.html` includes it.

- A status line: the draft, the published revision, and whether it's the site's theme.
- **Save draft**, **Save and publish** and **Save, publish and activate**, each with a short line saying what it does (linked to the button with `aria-describedby`).
- The publishing buttons and the note box show only to users who may publish. Others see a line saying which permission publishing needs.
- **Save, publish and activate** is left out when the theme is already the site's theme.
- **Save draft** comes first, so pressing Enter saves the draft.
- Django's **Delete** link, for users who may delete.

Its look is in `admin/save_publish.css`; it has no inline styles.
