# src/capy_theme/css/

**Writes the theme's stylesheet:** a published revision turned into CSS that overrides daisyUI's variables. This section also covers custom CSS and serves both files.

| File | Job |
| --- | --- |
| `stylesheet.py` | Assembles the whole stylesheet; the URL and version hash |
| `shape.py` + `shape.json` | Radii, sizes, border, depth, noise |
| `typography.py` + `type_settings.json` | The type scale |
| `backgrounds.py` | Background image variables and classes |
| `accessibility.py` | Reduce-motion and more-contrast rules |
| `custom.py` | Custom CSS: reading it, its URL, the permission |
| `views.py` | Serves `/theme/<version>.css` and `/theme/custom/<version>.css` |

Font rules (`fonts/css.py`) and logo-height rules (`images/logo_tag.py`) also feed into the stylesheet.
