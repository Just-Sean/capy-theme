# src/capy_theme/admin/fonts.py

**What it is:** the **font library** admin.

- **The list:** each font with a live **preview** in that font, its source and its number of files.
- **The font page:**
  - family, source, fallback, license, external stylesheet
  - a **Files** list where you upload WOFF2/WOFF/TTF/OTF files
  - each file is checked, converted to WOFF2 and trimmed to the chosen character set (`fonts/uploads.py`)
  - weight and style are read from the font if left blank
- **Import from Google Fonts:** a page where you type a family name and choose weights, italics and character sets (`fonts/google.py`).
