# src/capy_theme/templates/capy_theme/editor/components/forms.html

Sample **form fields**: text input, select, textarea, checkbox, toggle, radio and range, each with a label.

The form has `onsubmit="return false"` so nothing submits. That's an inline script, which a strict CSP would block (issue #214).
