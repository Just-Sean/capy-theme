# src/capy_theme/templates/capy_theme/editor/live_edit_components.html

**The live edit page's samples,** the same as the demo's home page:

- buttons (colors, styles and sizes)
- badges
- a card
- alerts
- a striped table
- form fields
- headings 1 to 6 with body text and a link

**Where it differs from the demo,** so the page works as a theme-building page:

- **Form fields:** they aren't inside a `<form>`, and the buttons are `type="button"`. Pressing Enter or clicking never reloads the page and loses the editor's unsaved changes.
- **Sample headings:** they have no size or weight classes. Utility classes would win over the theme's heading rules, so with none, the theme's heading scale and weight show.
- **Sample alerts:** they have no `role="alert"`, so screen readers don't read them out when the page loads.
