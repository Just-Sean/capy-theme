# src/capy_theme/static/capy_theme/editor/controls/actions.js

**Save draft**, **Revert**, **Save and publish** and **Save, publish and activate**, at the bottom of the panel. Each button has a line saying what it does, as on the admin's theme page (#273).

- **Save draft** POSTs the values to `save/` and rebuilds the panel from the returned state.
- **Revert** asks first, then throws away the unsaved changes: it cancels any preview still on its way, rebuilds the panel from the last saved state (`ui.saved`) and shows that draft's CSS again.
- **Save and publish** (only shown to users who may publish) asks first, saves any unsaved changes, then publishes with an optional note.
- **Save, publish and activate** does the same and also makes it the site's theme. It's not shown when the theme already is.
- After publishing, focus goes back to the button pressed, or to **Save and publish** when the activate button is gone.

It shows success or the server's errors, plus the "Unsaved changes" note.
