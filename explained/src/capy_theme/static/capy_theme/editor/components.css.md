# src/capy_theme/static/capy_theme/editor/components.css

**What it is:** **built, don't edit by hand.** About 100 KB of minified daisyUI 5.7.50 plus Tailwind 4.3.4, with only the classes the Components view's templates use.

- **Made by:** `scripts/build_components_css.py`. Rebuild it after changing those templates or updating daisyUI.
- **Why it ships:** it's committed and shipped so the Components view works in any project, even one without Tailwind or daisyUI.
- **Where it's used:** only inside the Components view's iframe, so it never touches the page being edited.
