# src/capy_theme/artifacts/daisyui_block.py

**What it is:** `build_block(theme, revision)` writes the theme as two daisyUI theme blocks: `<slug>-light` (the default) and `<slug>-dark` (when the device prefers dark).

```css
@plugin "daisyui/theme" { name: "main-light"; default: true; --color-primary: ...; }
```

It's for projects that compile the theme into their **own** Tailwind stylesheet instead of loading capy-theme's. Only daisyUI's own variables are included (colors, radii, sizes, border, depth, noise). Fonts, the type scale, logos and the rest need `{% theme_head %}`.
