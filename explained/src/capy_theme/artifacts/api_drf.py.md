# src/capy_theme/artifacts/api_drf.py

**What it is:** the same API as a **Django REST Framework view**, only imported when the project uses DRF. The benefit: with **drf-spectacular**, the endpoint appears in the project's generated API docs (Swagger or Redoc) automatically.

- **The serializers** only *describe* the response for the docs. The view returns exactly the same JSON and ETag as the plain view.
- **`ThemeAPIView`** sets its own rules: no login, no throttling, JSON only. That way a project's DRF defaults (like "login required") can't lock up this public API.
- drf-spectacular is optional. Without it, `extend_schema` does nothing.

capy-theme never requires DRF; it's a dev-only dependency for testing this.
