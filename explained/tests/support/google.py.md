# tests/support/google.py

**What it is:** `FakeGoogle`, a stand-in for Google Fonts. It answers the CSS API with realistic `@font-face` blocks and serves tiny fonts for the file downloads. It's passed to `import_family(download=...)`, so the Google Fonts tests never touch the network.
