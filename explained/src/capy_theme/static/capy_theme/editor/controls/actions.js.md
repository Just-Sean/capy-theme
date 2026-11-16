# src/capy_theme/static/capy_theme/editor/controls/actions.js

**Save draft**, **Revert** and **Publish**, at the bottom of the panel.

- **Save draft** POSTs the values to `save/` and rebuilds the panel from the returned state.
- **Revert** asks first, then throws away the unsaved changes: it cancels any preview still on its way, rebuilds the panel from the last saved state (`ui.saved`) and shows that draft's CSS again.
- **Publish** (only shown to users who may publish) saves any unsaved changes first, then publishes with an optional note.

It shows success or the server's errors, plus the "Unsaved changes" note.
