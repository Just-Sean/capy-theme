# src/capy_theme/colors/values.py

**What it is:** a theme's **final color and shape values** for one mode.

- **`effective_values(snapshot, scheme)`:** starts from the base theme's saved values and adds the shape overrides and color overrides. Then it fills in what wasn't set:
  - a color set without its text color gets a readable text color
  - a background set without its shades or text gets those worked out too

  Used everywhere values are needed: the stylesheet, contrast, API, tokens, email colors.
- **`contrast_report(values)`:** each color/text pair with its ratio and rating, for the admin's Contrast section and the editor's badges.
- **`draft_values(theme, scheme)`:** the same for an unpublished draft.
