# src/capy_theme/templates/capy_theme/editor/components/

One small template per sample in the Components view. Each is included twice, once with `mode` = `light` and once with `dark`, so any `id` or `name` uses `{{ mode }}` to stay unique. They're listed in `COMPONENTS` in `editor/components_view.py`. After changing them, rebuild `components.css` (`scripts/build_components_css.py`), because Tailwind only includes classes it finds.
