# src/capy_theme/templates/capy_theme/admin/save_publish.html

The theme page's **Save and publish** area at the bottom, in place of Django's own save buttons (#273). `theme_change_form.html` includes it.

- A status line: the draft, the published revision, whether it's the default theme, and, while a theme schedule is running, which theme the site is **showing now**.
- The optional note for the history comes first, above the buttons, for users who may publish. What was typed is kept if the page comes back with errors.
- **Save draft**, **Save and publish** and **Save, publish and activate**, each with a short line saying what it does (linked to the button with `aria-describedby`). They use the admin's `button` class, so they look like its other buttons.
- The two publishing buttons ask first (a `data-capy-confirm` question, shown by `admin/confirm.js`): "Save and publish this theme? Visitors will see it wherever it's used." and "Save, publish and make this the default theme? Visitors will see it (unless a theme schedule is running)." **Save draft** doesn't.
- The publishing buttons show only to users who may publish. Others see: "You can save drafts. To publish, ask someone who can publish themes", naming the permission.
- **Save, publish and activate** is left out when the theme is already the default theme (a line then says "This is already the default theme, so Save and publish updates it."), and in a popup.
- **Save draft** comes first, so pressing Enter saves the draft.
- Below the area, in a `.submit-row` of its own so it looks like Django's: the **Delete** link, for users who may delete, keeping the list's filters. It's hidden when Django's `show_delete` is False. Users who may only view get a **Close** link back to the list (with its filters) instead.

Its look is in `admin/save_publish.css`; it has no inline styles or scripts.
