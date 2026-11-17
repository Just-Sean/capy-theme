# src/capy_theme/fonts/unpacking.py

**What it is:** the check that stops a small compressed font from unpacking into a huge amount of data (#191). It runs before fontTools sees the file.

WOFF and WOFF2 fonts are compressed, and fontTools unpacks them with no limit, so a file of a few KB could make the server use gigabytes of memory.

**`check(data)`** looks at WOFF and WOFF2 files (TTF and OTF aren't compressed, so they pass straight through):

1. **Adds up the sizes the file says it unpacks to** and refuses it if that's over `CAPY_THEME_FONT_MAX_UNPACKED_BYTES` (30 MB by default; real fonts unpack to well under that).
2. **Unpacks each compressed part a little at a time**, stopping as soon as it gives more than the file said. So a file that lies about its sizes is refused before it can use more memory than the limit.

It also refuses font collections (several fonts in one file). Refusals are `ValidationError`s with a message the admin shows; a file too broken to read raises the same errors fontTools would, so it's reported as "isn't a font".

This only limits unpacking. Reading the font can still be costly, so that runs in its own process with limits: see `converting.py`.
