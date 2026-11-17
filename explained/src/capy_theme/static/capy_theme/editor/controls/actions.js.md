# src/capy_theme/static/capy_theme/editor/controls/actions.js

**Save draft**, **Revert**, **Save and publish** and **Save, publish and activate**, at the bottom of the panel. Each button has a line saying what it does, as on the admin's theme page (#273); each line makes sense on its own.

- **Save draft** POSTs the values to `save/` and rebuilds the panel from the returned state.
- **Revert** asks first, then throws away the unsaved changes: it cancels any preview still on its way, rebuilds the panel from the last saved state (`ui.saved`) and shows that draft's CSS again.
- **Note for the history:** an optional box with a visible label, above the publishing buttons, so it's filled in first. Its length limit comes from the state (`note_max`). What's typed is kept in `ui.publishNote`, so it survives the panel being rebuilt (Save draft, a failed publish), and is cleared once it's published.
- **Save and publish** (only shown to users who may publish) asks first ("Save and publish this theme? Visitors will see it wherever it's used."), saves any unsaved changes, then publishes with the note.
- **Save, publish and activate** does the same, asking "Save, publish and make this the default theme? Visitors will see it (unless a theme schedule is running).", and also makes it the default theme. It's not shown when the theme already is (`is_default`); a line then says "This is already the default theme, so Save and publish updates it."
- After activating, the message says it's now the default theme, or, if a running theme schedule is showing another theme, names that one.
- Users who may not publish see: "You can save drafts. To publish, ask someone who can publish themes", naming the permission.
- After publishing, focus goes back to the button pressed, or to **Save and publish** when the activate button is gone.

It shows success or the server's errors, plus the "Unsaved changes" note.
