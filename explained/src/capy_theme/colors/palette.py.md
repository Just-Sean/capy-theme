# src/capy_theme/colors/palette.py

**What it is:** the editor's **Suggest colors**.

- **`from_primary(primary)`:** three sets (analogous, complementary, triadic). Each has a secondary and an accent at the same lightness and strength as the primary with the hue shifted, plus a dark near-gray neutral.
- **`from_logo(file)`:** the main colors of the theme's logo image, worked out with Pillow, offered as a set.

Suggestions are only shown; nothing is saved unless you click one and then Save.
