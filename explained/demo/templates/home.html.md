# demo/templates/home.html

**What it is:** the demo's home page, a showcase of daisyUI components for seeing a theme's effect at a glance:

- buttons in every color, style and size
- badges
- a card
- alerts
- a striped table
- form fields (text, select, textarea, checkbox, toggle, radio, slider)
- all six heading levels and a link

It extends `base.html`. Nothing here is capy-theme-specific: the theme changes how these look through daisyUI's CSS variables.

The sample form has `onsubmit="return false"` so it doesn't submit. That's an inline script, which a strict Content Security Policy would block (see issue #214).
