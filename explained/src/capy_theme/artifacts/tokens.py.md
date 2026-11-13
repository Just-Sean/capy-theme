# src/capy_theme/artifacts/tokens.py

**What it is:** `build_tokens(artifacts)` turns the theme into **W3C Design Tokens (format 2025.10)**, the standard that design tools (Figma, Tokens Studio, Style Dictionary) and native app builds read.

- **`light` and `dark` groups,** each with:
  - `color`: all 20, as OKLCH components with a hex fallback; grays get hue `"none"`
  - `shape`: radii and sizes as dimensions; depth and noise as numbers
- **`font`:** a family token per role.
- **`type`:** the type scale.

Every token states its `$type`. The tests validate the output against the format's official JSON Schema.
