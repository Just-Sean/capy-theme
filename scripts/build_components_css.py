"""Build the live editor's Components view stylesheet with Tailwind CSS and daisyUI.

Writes src/capy_theme/static/capy_theme/editor/components.css from
scripts/components.tailwind.css, scanning only the Components view's templates. Run
it from the repo root after changing those templates or updating daisyUI:

    uv run python scripts/build_components_css.py

It uses the Tailwind CLI that django-tailwind-cli downloads for the demo site.
If it isn't there yet, run `uv run python demo/manage.py tailwind build` once.
"""

import re
import subprocess  # noqa: S404
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "scripts" / "components.tailwind.css"
OUTPUT = REPO_ROOT / "src" / "capy_theme" / "static" / "capy_theme" / "editor" / "components.css"
CLI_DIR = REPO_ROOT / "demo" / ".django_tailwind_cli"
DAISYUI_PLUGIN = REPO_ROOT / "demo" / "tailwind" / "daisyui.mjs"


def find_cli():
    """Return the newest downloaded Tailwind CLI, or None."""
    candidates = sorted(CLI_DIR.glob("tailwindcss-*"))
    return candidates[-1] if candidates else None


def main():
    cli = find_cli()
    if cli is None:
        sys.exit(
            "Tailwind CLI not found. Run `uv run python demo/manage.py tailwind build` once "
            "to download it, then run this again."
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        [str(cli), "--input", str(SOURCE), "--output", str(OUTPUT), "--minify"],
        cwd=REPO_ROOT,
        check=True,
    )
    # Minifying drops daisyUI's licence comment, so add the notice back.
    version = re.search(r'var version = "([^"]+)"', DAISYUI_PLUGIN.read_text(encoding="utf-8"))
    number = version.group(1) if version else ""
    banner = f"/*! daisyUI {number} | MIT License | https://daisyui.com */\n"
    OUTPUT.write_text(banner + OUTPUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
