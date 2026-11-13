# src/capy_theme/colors/

**Everything about color:**

- **the 20 daisyUI colors:** names, groups, labels
- **color math:** converting any CSS color to OKLCH, WCAG contrast, readable text colors, background shades
- **each mode's final values:** the base theme with the overrides merged in
- **contrast reports**
- **palette suggestions**
- **the admin's color field**

The heavy lifting uses the `coloraide` library.

| File | Job |
| --- | --- |
| `names.py` + `colors.json` | The 20 colors, their groups and labels |
| `color_math.py` | Conversions, contrast, readable text, shades, focus color, hex |
| `values.py` | A mode's final values, and the contrast report |
| `palette.py` | Suggestions from the primary color or the logo |
| `fields.py` | The admin's color text box and picker |
