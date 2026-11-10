"""Fetch the curated font collection from Fontsource into the module's static files.

Downloads each font's npm package (pinned below) from the npm registry and keeps
its Latin regular (400), bold (700) and italic (400) WOFF2 files, where the font
has them, plus its licence. Writes:

- src/capy_theme/static/capy_theme/fonts/<id>/  the WOFF2 files and LICENSE
- src/capy_theme/fonts/curated.json              what the add-fonts command reads

Run it from the repo root after changing the list:

    uv run python scripts/fetch_curated_fonts.py

All fonts here are under the SIL Open Font License 1.1 (checked from each package).
"""

import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC = REPO_ROOT / "src" / "capy_theme" / "static" / "capy_theme" / "fonts"
MANIFEST = REPO_ROOT / "src" / "capy_theme" / "fonts" / "curated.json"
PACKAGE_URL = "https://registry.npmjs.org/@fontsource/{id}/-/{id}-{version}.tgz"
WANTED = [(400, "normal"), (700, "normal"), (400, "italic")]

SANS = "ui-sans-serif, system-ui, sans-serif"
SERIF = 'ui-serif, Georgia, Cambria, "Times New Roman", serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'

# (Fontsource id, family, category, fallback stack, version)
CURATED = [
    ("inter", "Inter", "sans", SANS, "5.3.0"),
    ("roboto", "Roboto", "sans", SANS, "5.3.0"),
    ("open-sans", "Open Sans", "sans", SANS, "5.3.0"),
    ("lato", "Lato", "sans", SANS, "5.3.0"),
    ("montserrat", "Montserrat", "sans", SANS, "5.3.0"),
    ("source-sans-3", "Source Sans 3", "sans", SANS, "5.3.1"),
    ("nunito", "Nunito", "sans", SANS, "5.3.0"),
    ("poppins", "Poppins", "sans", SANS, "5.3.0"),
    ("work-sans", "Work Sans", "sans", SANS, "5.3.0"),
    ("ibm-plex-sans", "IBM Plex Sans", "sans", SANS, "5.3.0"),
    ("dm-sans", "DM Sans", "sans", SANS, "5.3.0"),
    ("raleway", "Raleway", "sans", SANS, "5.3.0"),
    ("figtree", "Figtree", "sans", SANS, "5.3.0"),
    ("manrope", "Manrope", "sans", SANS, "5.3.0"),
    ("outfit", "Outfit", "sans", SANS, "5.3.0"),
    ("merriweather", "Merriweather", "serif", SERIF, "5.3.0"),
    ("lora", "Lora", "serif", SERIF, "5.3.0"),
    ("playfair-display", "Playfair Display", "serif", SERIF, "5.3.0"),
    ("source-serif-4", "Source Serif 4", "serif", SERIF, "5.3.1"),
    ("libre-baskerville", "Libre Baskerville", "serif", SERIF, "5.3.0"),
    ("eb-garamond", "EB Garamond", "serif", SERIF, "5.3.0"),
    ("crimson-pro", "Crimson Pro", "serif", SERIF, "5.3.0"),
    ("pt-serif", "PT Serif", "serif", SERIF, "5.3.0"),
    ("ibm-plex-serif", "IBM Plex Serif", "serif", SERIF, "5.3.0"),
    ("jetbrains-mono", "JetBrains Mono", "mono", MONO, "5.3.0"),
    ("fira-code", "Fira Code", "mono", MONO, "5.3.0"),
    ("source-code-pro", "Source Code Pro", "mono", MONO, "5.3.1"),
    ("ibm-plex-mono", "IBM Plex Mono", "mono", MONO, "5.3.0"),
    ("oswald", "Oswald", "display", SANS, "5.3.0"),
    ("bebas-neue", "Bebas Neue", "display", SANS, "5.3.0"),
]


def fetch(font_id, version):
    url = PACKAGE_URL.format(id=font_id, version=version)
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (fixed https URL)
        return response.read()


def main():
    if STATIC.exists():
        shutil.rmtree(STATIC)
    manifest = []
    for font_id, family, category, fallback, version in CURATED:
        package = fetch(font_id, version)
        folder = STATIC / font_id
        folder.mkdir(parents=True)
        files = []
        with tarfile.open(fileobj=io.BytesIO(package), mode="r:gz") as tar:
            names = set(tar.getnames())
            meta = json.load(tar.extractfile("package/package.json"))
            if meta.get("license") != "OFL-1.1":
                raise SystemExit(f"{font_id}: unexpected licence {meta.get('license')!r}")
            for weight, style in WANTED:
                name = f"package/files/{font_id}-latin-{weight}-{style}.woff2"
                if name not in names:
                    continue
                target = folder / f"{font_id}-latin-{weight}-{style}.woff2"
                target.write_bytes(tar.extractfile(name).read())
                files.append({"weight": weight, "style": style, "path": f"{font_id}/{target.name}"})
            (folder / "LICENSE").write_bytes(tar.extractfile("package/LICENSE").read())
        manifest.append(
            {
                "id": font_id,
                "family": family,
                "category": category,
                "fallback": fallback,
                "version": version,
                "licence": "SIL Open Font License 1.1",
                "files": files,
            }
        )
        print(f"{family}: {len(files)} files")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in STATIC.rglob("*")) // 1024
    print(f"Wrote {len(manifest)} fonts ({size} KB) to {STATIC.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
