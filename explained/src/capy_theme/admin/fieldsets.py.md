# src/capy_theme/admin/fieldsets.py

**What it is:** `THEME_FIELDSETS`, the theme page's sections, top to bottom:

1. Name (name and slug), with a tip pointing to **Edit live**
2. Publishing (status)
3. Base themes
4. Branding
5. Icon
6. Logos
7. Fonts
8. Type scale
9. Colors (light and dark; Basic, Advanced and Expert)
10. Contrast
11. Shape and effects
12. Mode
13. Visitors ("offered to visitors")
14. Backgrounds
15. Sharing image
16. Custom CSS (only for people who may edit it)
17. Advanced (the stored settings, ID and dates)

Every section can be folded (a loop at the end gives each one Django's `collapse` class, #259). On the page they're grouped into tabs (see `tabs.py`), and every section starts folded; one with errors opens (#267).
