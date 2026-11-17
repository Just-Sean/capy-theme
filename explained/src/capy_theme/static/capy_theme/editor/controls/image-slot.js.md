# src/capy_theme/static/capy_theme/editor/controls/image-slot.js

**What it is:** the control for one image slot and mode in the editor (#271), `ui.slotControl(spec, mode)`. `image-sections.js` uses it for every slot.

Each control shows:

- the slot's name and what it's for (the same text as the admin)
- the current image, or what an empty slot does
- **Current image:** a choice of this slot's earlier uploads ("None", or "Same as light" for dark)
- **Alt text of the current image.** An edit goes into `ui.changes.alts` and is saved with Save draft.
- **Upload a new image** (folded): a file, its alt text and **Upload and use**

**Uploading:** the file goes to `upload/`, where the server checks, cleans and stores it straight away. It's then chosen in the unsaved changes, so Save draft keeps the choice and Revert drops it. The image stays in the theme's list either way. While uploading, the button and the slot's choice are off, and the "uploading" state is kept outside the redraw, so nothing can start a second upload (#222). After an upload, every box for that slot (light and dark) refreshes its list, without touching a file chosen there. If the editor was saved or reverted meanwhile, the new image is only added to the lists, not chosen, and the status line says so; if it was closed, nothing more happens. A failed upload turns the button back on without redrawing, so the chosen file stays.
