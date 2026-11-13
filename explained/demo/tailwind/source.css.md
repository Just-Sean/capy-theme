# demo/tailwind/source.css

**What it is:** the Tailwind input file, compiled into `demo/static/css/tailwind.css`.

**What it says:**

- `@import "tailwindcss";` brings in Tailwind.
- `@source "../templates";` and `@source "../../src/capy_theme/templates";` tell Tailwind which templates to scan for class names. It only outputs classes it finds.
- `@plugin "./daisyui.mjs";` adds daisyUI.

It deliberately sets **no fonts**, so the theme's fonts can apply.

This is also the example the README's "Tailwind and daisyUI for a new project" section follows.
