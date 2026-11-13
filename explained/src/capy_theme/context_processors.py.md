# src/capy_theme/context_processors.py

**What it is:** a context processor. A project adds `capy_theme.context_processors.theme` to its template settings, and then every template gets a `{{ theme }}` variable.

**What `theme` holds** (from the **published** revision, never the draft):

- name, slug and revision number
- the light and dark base theme names
- the stylesheet URL
- **branding:** site name, tagline, logo URL, logo alt text
- the background image URLs
- the default mode, whether visitors can switch, and the mode this visitor sees
- **`email_colors`:** the light-mode colors as hex, because email programs can't use OKLCH or CSS variables

`theme` is `None` when no theme is published. The demo's header uses it, e.g. `{{ theme.tagline }}`.
