# src/capy_theme/fonts/google.py

**What it is:** **Import from Google Fonts**. The server downloads a family **once** and stores it like an upload, so pages load it from your own site and **visitors' browsers never contact Google**. That's better for privacy and GDPR.

**`import_family(family, weights, italic, subsets)`:**

1. Checks the name: letters, digits and spaces, up to 100 characters. Refuses fonts already in the library.
2. Asks Google's CSS API which WOFF2 files exist for the chosen weights, italics and character sets.
3. Downloads each file. It only accepts files from `fonts.gstatic.com`, uses an https timeout, and passes each through `uploads.prepare`.
4. Saves it all in one database transaction. Files shared between weights (variable fonts) are stored once.
5. Logs the import. If Google can't be reached, it logs a warning and shows a clear error.

`download` is passed in, so the tests use a fake Google and never touch the internet.
