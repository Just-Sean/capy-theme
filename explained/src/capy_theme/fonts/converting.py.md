# src/capy_theme/fonts/converting.py

**What it is:** the fontTools work on a font (reading, trimming, converting to WOFF2), run in a **separate process** with memory and time limits (#191).

Even a small font can make fontTools use gigabytes of memory or minutes of time, so `uploads.prepare()` doesn't run it in the web server's own process. It starts a fresh one (`spawn`) that runs `work()`. This module doesn't use Django, so that process starts quickly.

- **`work(answer, data, subset, memory, seconds)`:** the separate process. It caps its own memory and CPU time (`limit()`), converts the font and sends the outcome back. The limits come from `CAPY_THEME_FONT_MAX_MEMORY_BYTES` (512 MB) and `CAPY_THEME_FONT_MAX_SECONDS` (30 s); the server also stops waiting after that time.
- **`outcome(data, subset)`:** says what happened: the font, "refused" (e.g. it has none of the subset's characters), "not a font" or "too complex" (it ran out of memory). Anything else is a bug and ends the process with its error on the server's error output.
- **`convert(data, subset)`:** reads the font, trims it to the character subset if one is chosen, reads its weight, italic flag and family name, and saves it as WOFF2.
- **`SUBSETS`** (from `subsets.json`) and **`PARSE_ERRORS`** (what fontTools raises for files that aren't fonts) are shared with `uploads.py`.

`limit()` does nothing on Windows, which has no process limits; the README's advice on worker timeouts and memory limits is the backstop.
