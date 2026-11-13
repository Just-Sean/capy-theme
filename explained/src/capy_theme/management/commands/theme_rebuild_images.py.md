# src/capy_theme/management/commands/theme_rebuild_images.py

**`manage.py theme_rebuild_images [<slug>]`** remakes every generated image, for every theme or just one:

- the logo copies and sharing-image crops, from the uploaded originals
- the icons of published revisions

Use it after a capy-theme update changes how they're made, or for logos migration 0010 moved into the main slot (they have no smaller copies until then).
