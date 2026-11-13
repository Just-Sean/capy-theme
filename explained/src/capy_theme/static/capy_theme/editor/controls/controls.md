# src/capy_theme/static/capy_theme/editor/controls/

One script per editor panel section. Each adds itself to `ui.sections` with an `order`, a `build(state)` that makes its controls, and optionally a `fill()` that shows the latest values.

Every change updates `ui.changes` and calls `ui.update()`, which previews it straight away. Nothing is saved until **Save draft**.
