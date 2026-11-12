"""Generate src/capy_theme/themes/builtin_themes.json from the daisyUI package.

Downloads the published daisyUI package (DAISYUI_VERSION) from npm and reads two
data files from it:

- theme/object.js: every built-in theme's values
- functions/themeOrder.js: daisyUI's own order for listing themes

Run it from the repo root after changing DAISYUI_VERSION:

    uv run python scripts/generate_builtin_themes.py

It also checks that the demo site's daisyUI plugin (demo/tailwind/daisyui.mjs)
is the same version, and warns if not, so the catalog matches what the demo shows.
"""

import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

DAISYUI_VERSION = "5.7.50"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "src" / "capy_theme" / "themes" / "builtin_themes.json"
DEMO_PLUGIN = REPO_ROOT / "demo" / "tailwind" / "daisyui.mjs"
PACKAGE_URL = "https://registry.npmjs.org/daisyui/-/daisyui-{version}.tgz"


def download_package(version):
    """Return the daisyUI package (a .tgz) as bytes."""
    url = PACKAGE_URL.format(version=version)
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 (fixed https URL)
        return response.read()


def read_member(package, name):
    """Return the text of one file inside the package, e.g. "theme/object.js"."""
    with tarfile.open(fileobj=io.BytesIO(package), mode="r:gz") as tar:
        member = tar.extractfile(f"package/{name}")
        if member is None:
            raise SystemExit(f"{name} not found in the daisyUI package")
        return member.read().decode("utf-8")


def parse_js_export(source):
    """Parse a file of the form `export default <JSON>;` into Python data."""
    source = source.strip()
    prefix = "export default"
    if not source.startswith(prefix):
        raise ValueError("expected the file to start with 'export default'")
    body = source[len(prefix) :].strip().rstrip(";").strip()
    # themeOrder.js is a JS array that may end with a trailing comma; JSON doesn't allow one.
    body = re.sub(r",\s*([\]}])", r"\1", body)
    return json.loads(body)


def build_themes(themes, order):
    """Return the themes as {name: {"scheme": ..., "values": {...}}} in daisyUI's order."""
    if set(order) != set(themes):
        raise ValueError(
            f"themeOrder.js and object.js list different themes: {sorted(set(order) ^ set(themes))}"
        )
    result = {}
    for name in order:
        values = dict(themes[name])
        scheme = values.pop("color-scheme")
        if scheme not in ("light", "dark"):
            raise ValueError(f"{name}: unexpected color-scheme {scheme!r}")
        result[name] = {"scheme": scheme, "values": dict(sorted(values.items()))}
    return result


def render(themes, version):
    """Return builtin_themes.json: the daisyUI version and every theme's scheme and values.

    Generated: don't edit it by hand. capy_theme.themes.catalog reads it.
    """
    data = {"daisyui_version": version, "themes": themes}
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def demo_plugin_version():
    """Return the daisyUI version recorded in the demo's daisyui.mjs, or None."""
    if not DEMO_PLUGIN.exists():
        return None
    match = re.search(r'var version = "([^"]+)"', DEMO_PLUGIN.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def main():
    package = download_package(DAISYUI_VERSION)
    themes = parse_js_export(read_member(package, "theme/object.js"))
    order = parse_js_export(read_member(package, "functions/themeOrder.js"))
    OUTPUT.write_text(render(build_themes(themes, order), DAISYUI_VERSION), encoding="utf-8")
    output = OUTPUT.relative_to(REPO_ROOT)
    print(f"Wrote {len(themes)} daisyUI {DAISYUI_VERSION} themes to {output}")

    demo_version = demo_plugin_version()
    if demo_version != DAISYUI_VERSION:
        print(
            f"Warning: the demo's daisyui.mjs is version {demo_version}, not {DAISYUI_VERSION}. "
            "Replace demo/tailwind/daisyui.mjs and daisyui-theme.mjs with the same release.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
