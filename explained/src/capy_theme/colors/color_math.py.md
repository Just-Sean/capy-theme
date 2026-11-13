# src/capy_theme/colors/color_math.py

**What it is:** the color calculations, using `coloraide`.

- **`to_oklch(value)`:** any CSS color (hex, rgb, hsl, oklch, a name) → `oklch(...)` text, daisyUI's format. Raises ValueError for anything that isn't a color.
- **`contrast(a, b)`:** the WCAG 2 contrast ratio (1–21).
- **`rating(ratio)`:** AAA (7+), AA (4.5+), or fail. These are warnings only.
- **`readable_text(background)`:** a text color for a background. It prefers a very light or very dark tint of the same hue, and falls back to pure white or black if the tint can't reach 4.5:1.
- **`shade(background, step)`:** a slightly darker background for base-200/300, the way daisyUI does it. Very dark backgrounds get lighter shades instead.
- **`focus_color(values)`:** the keyboard focus outline color: primary if it has 3:1 contrast with the background, else the text color.
- **`to_hex()`, `hex_colors()`:** hex versions, for email and browser-color tags.
