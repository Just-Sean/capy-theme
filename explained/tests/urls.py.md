# tests/urls.py

**What it is:** the stand-in project's URLs:

- the admin
- capy-theme's URLs under `/theme/`
- an ordinary project page at `/page/` that uses `{% theme_html_attrs %}` and `{% theme_head %}`, like any real page

The editor and head-tag tests load `/page/`.
