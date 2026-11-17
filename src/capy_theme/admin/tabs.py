"""How the theme admin page's sections are grouped into tabs.

Presentation only: the page renders every section inside its tab's panel, and
`static/capy_theme/admin/tabs.js` turns the panels into tabs and opens the sections
(every section can be folded, #259). Without JavaScript the panels simply follow each
other, every section folded; each opens with a click.
"""

from django.utils.text import slugify

from .form_colors import color_fieldsets

# (tab label, section names or inline model names). Sections not listed here land in
# a final "More" tab, so a section added later is never lost.
THEME_TABS = [
    ("General", ["Name", "Publishing", "Base themes", "Mode", "Visitors"]),
    ("Branding", ["Branding", "Icon", "Logos", "Backgrounds", "Sharing image"]),
    ("Fonts", ["Fonts", "Type scale"]),
    ("Light colors", [name for name, _ in color_fieldsets() if name.startswith("Light")]),
    ("Dark colors", [name for name, _ in color_fieldsets() if name.startswith("Dark")]),
    ("Shape and contrast", ["Shape and effects", "Contrast"]),
    ("Images", ["themeasset"]),
    ("Revisions", ["themerevision"]),
    ("Advanced", ["Custom CSS", "Advanced"]),
]

LEFTOVER_TAB = "More"


def theme_tabs(adminform, inline_formsets):
    """The tabs to render, in order, each with its sections and inline lists.

    Every section keeps its original position number (`index`), so the HTML ids
    Django gives it don't change. Tabs with nothing in them are left out. Each tab's
    `id` comes from its label, so the browser remembers the same tab even when the set
    of tabs differs; `order` is its place in the row.
    """
    tabs = {label: {"label": label, "fieldsets": [], "inlines": []} for label, _ in THEME_TABS}
    tabs[LEFTOVER_TAB] = {"label": LEFTOVER_TAB, "fieldsets": [], "inlines": []}
    home = {item: label for label, items in THEME_TABS for item in items}

    for index, fieldset in enumerate(adminform):
        entry = {"fieldset": fieldset, "index": index}
        tabs[home.get(fieldset.name, LEFTOVER_TAB)]["fieldsets"].append(entry)
    for formset in inline_formsets:
        tabs[home.get(formset.opts.model._meta.model_name, LEFTOVER_TAB)]["inlines"].append(formset)

    rendered = [tab for tab in tabs.values() if tab["fieldsets"] or tab["inlines"]]
    for order, tab in enumerate(rendered):
        tab["id"] = "capy-tab-" + slugify(tab["label"])
        tab["order"] = order
    return rendered
