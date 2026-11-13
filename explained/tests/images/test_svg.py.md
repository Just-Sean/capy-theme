# tests/images/test_svg.py

**What it tests:** Tests for SVG cleaning (issue #33).

**Code it covers:** `src/capy_theme/images/`

**Its 23 tests** (each name says what must hold):

- the issue check script is removed
- event handlers are removed
- embedded html is removed
- external references are removed
- internal references are kept
- javascript links are removed but their contents kept
- embedded raster images are kept
- animation and other namespaces are removed
- text after a removed element is kept
- doctypes and entities are rejected
- utf16 cant hide a doctype
- other text is rejected
- svg without xmlns gets one
- size comes from the viewbox or width and height
- prepare image takes svgs
- an uploaded svg is stored clean
- slots that cant use svg ask for a png
- editor marks slots without svg
- too many elements are rejected
- text after an empty link is kept
- text after a removed element joins the previous sibling
- size falls back to width and height when the viewbox isnt numbers
- defusedxml refuses entities even without the first check

Run just this file with `uv run pytest tests/images/test_svg.py`.
