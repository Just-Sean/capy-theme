# src/capy_theme/editor/mount.py

**What it is:** `mount(request)` returns the editor's tags for `{% theme_head %}`. It renders `templates/capy_theme/editor/mount.html` with the theme, the endpoint URLs and whether to show the corner button (`CAPY_THEME_EDITOR_BUTTON`).

It returns nothing for visitors and anyone who can't edit, so **they never download any editor files**. This is why the editor works on every page of any project with no extra setup.
