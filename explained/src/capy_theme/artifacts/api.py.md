# src/capy_theme/artifacts/api.py

**What it is:** the public, read-only **JSON API** at `/theme/api.json`, for React or Vue front ends, mobile apps and other services. It serves `get_artifacts()`.

- **`payload(request)`:** the data and an **ETag**, a hash of the data.
- **`theme_api`:** the plain Django view.
  - It's a 404 with `{"error": ...}` if nothing is published.
  - It answers **304 Not Modified** when the client sends back a matching ETag in `If-None-Match`.
  - Responses are cacheable for 60 seconds.
- **`api_mode()` / `api_view()`:** picks the view once, when the URLs load, from `CAPY_THEME_API`:
  - `"auto"` uses DRF if the project has it
  - `"drf"` always uses DRF, and errors if DRF isn't installed
  - `"django"` always uses the plain view

capy-theme sets no CORS headers. A project allows other domains itself, e.g. with `django-cors-headers`.
