# src/capy_theme/migrations/0010_logo_slots.py

**Data migration.** It moves each theme's single logo (from 0005) into the new **main logo slot** as a `ThemeAsset` (reading its size with Pillow), then removes the old field. Logos moved this way have no smaller copies until `theme_rebuild_images` is run.
