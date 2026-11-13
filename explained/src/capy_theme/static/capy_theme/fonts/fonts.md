# src/capy_theme/static/capy_theme/fonts/

**The 30 bundled open-license fonts:** one folder per font, each with its WOFF2 files (Latin regular, bold and italic, where the font has them) and its `LICENSE`. All are under the SIL Open Font License 1.1 and come from Fontsource.

They're **generated** by `scripts/fetch_curated_fonts.py`, together with the list `src/capy_theme/fonts/curated.json`; don't edit them by hand. They aren't used directly from here: `manage.py capy_theme_add_fonts` copies them into the project's media storage and adds them to the font library, so they work like uploaded fonts.

Each folder gets one explanation file (`<font>/<font>.md`) instead of one per font file, as agreed.

| Folder | Family | Kind | Files |
| --- | --- | --- | --- |
| `inter/` | Inter | sans-serif | 3 |
| `roboto/` | Roboto | sans-serif | 3 |
| `open-sans/` | Open Sans | sans-serif | 3 |
| `lato/` | Lato | sans-serif | 3 |
| `montserrat/` | Montserrat | sans-serif | 3 |
| `source-sans-3/` | Source Sans 3 | sans-serif | 3 |
| `nunito/` | Nunito | sans-serif | 3 |
| `poppins/` | Poppins | sans-serif | 3 |
| `work-sans/` | Work Sans | sans-serif | 3 |
| `ibm-plex-sans/` | IBM Plex Sans | sans-serif | 3 |
| `dm-sans/` | DM Sans | sans-serif | 3 |
| `raleway/` | Raleway | sans-serif | 3 |
| `figtree/` | Figtree | sans-serif | 3 |
| `manrope/` | Manrope | sans-serif | 2 |
| `outfit/` | Outfit | sans-serif | 2 |
| `merriweather/` | Merriweather | serif | 3 |
| `lora/` | Lora | serif | 3 |
| `playfair-display/` | Playfair Display | serif | 3 |
| `source-serif-4/` | Source Serif 4 | serif | 3 |
| `libre-baskerville/` | Libre Baskerville | serif | 3 |
| `eb-garamond/` | EB Garamond | serif | 3 |
| `crimson-pro/` | Crimson Pro | serif | 3 |
| `pt-serif/` | PT Serif | serif | 3 |
| `ibm-plex-serif/` | IBM Plex Serif | serif | 3 |
| `jetbrains-mono/` | JetBrains Mono | monospace | 3 |
| `fira-code/` | Fira Code | monospace | 2 |
| `source-code-pro/` | Source Code Pro | monospace | 3 |
| `ibm-plex-mono/` | IBM Plex Mono | monospace | 3 |
| `oswald/` | Oswald | display | 2 |
| `bebas-neue/` | Bebas Neue | display | 1 |
