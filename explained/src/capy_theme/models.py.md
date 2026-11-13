# src/capy_theme/models.py

**What it is:** Django looks for an app's models in `models.py`. Here each section keeps its own models, and this file just imports them all in one place:

| Model | Defined in | What it is |
| --- | --- | --- |
| `Theme` | `themes/models/theme.py` | A theme and its draft |
| `ThemeRevision` | `themes/models/revision.py` | A published, frozen version of a theme |
| `ThemeAssignment`, `SiteTheme`, `ScheduledTheme` | `themes/models/assignment.py` | Which theme is live: default, per domain, scheduled |
| `Font`, `FontFile` | `fonts/models.py` | The font library |
| `ThemeAsset`, `ThemeAssetVariant` | `images/models.py` | Uploaded images and their generated copies |

The docstring reminds you to link to users with `settings.AUTH_USER_MODEL`, never a project's User class.
