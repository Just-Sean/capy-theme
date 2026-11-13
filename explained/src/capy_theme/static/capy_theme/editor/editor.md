# src/capy_theme/static/capy_theme/editor/

**The live editor's front end.** It's plain JavaScript and CSS: no framework, no Tailwind or daisyUI classes. That keeps it working and looking the same on any page of any project, and under a strict CSP (styles are applied through constructed stylesheets, not `<style>` tags).

| File | Job |
| --- | --- |
| `editor.js` | The shell: the corner button, banner, panel, loading state, previewing, closing |
| `editor.css` | The panel's look, and the page making room for it |
| `components.css` | daisyUI + Tailwind for the Components view's iframe (built) |
| `controls/` | One file per panel section |

They're loaded in order by `templates/capy_theme/editor/mount.html`: `editor.js`, then `controls/core.js`, then the sections.
