# src/capy_theme/admin/fieldsets.py

**What it is:** `THEME_FIELDSETS`, the theme page's sections, top to bottom:

1. Name (name and slug), with a tip pointing to **Edit live**
2. Publishing (status)
3. Base themes
4. Branding
5. Icon
6. Logos: just the main logo (light and dark) and the header heights
7. More logo versions (optional): stacked, mark and wordmark (light and dark), email and print (light only). Empty ones use the main logo.
8. Fonts
9. Type scale
10. Colors (light and dark; Basic, Advanced and Expert)
11. Contrast
12. Shape and effects
13. Mode
14. Visitors ("offered to visitors")
15. Backgrounds
16. Sharing image
17. Custom CSS (only for people who may edit it)
18. Advanced (the stored settings, ID and dates)

The image sections say an image can be uploaded or an earlier one picked right there; each slot explains itself (#271).

Every section can be folded (a loop at the end gives each one Django's `collapse` class, #259). On the page they're grouped into tabs (see `tabs.py`), and every section starts folded (#267). Django shows a section with errors unfolded.
