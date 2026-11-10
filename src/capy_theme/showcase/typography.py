"""Showcase data: fonts and type samples."""

SAMPLE_CHARACTERS = {
    "latin": "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 "
    "!?.,:;'\"()[]{}&@#%*+-=/ €£$",
    "latin-ext": "ĀāĂăĆćČčĐđĘęĞğİıŁłŃńŐőŒœŘřŞşŠšŢţŮůŰűŸŹźŽž",
    "cyrillic": "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ абвгдежзийклмнопрстуфхцчшщъыьэюя",
    "cyrillic-ext": "ЀЁЂЃЄЅІЇЈЉЊЋЌЍЎЏ ѐёђѓєѕіїјљњћќѝўџ",
    "greek": "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ αβγδεζηθικλμνξοπρστυφχψω",
    "greek-ext": "ἀἁἂἃἄἅἆἇἐἑἒἓἔἕ",
    "vietnamese": "ẠẢẤẦẨẪẬẮẰẲẴẶ ạảấầẩẫậắằẳẵặ ĂÂĐÊÔƠƯ ăâđêôơư",
}


def typography(revision):
    """The showcase's font and type data: each role's font, weights and the type settings."""
    from ..css.typography import heading_sizes
    from ..fonts.library import DEFAULT_FALLBACK, ROLES, stack

    fonts = (revision.snapshot.get("fonts") if revision else None) or {}
    settings = revision.snapshot.get("settings", {}) if revision else {}
    roles = []
    subsets = {"latin"}
    for role, role_label in ROLES.items():
        font = fonts.get(role)
        if font is None:
            roles.append(
                {"role": role, "label": role_label, "font": None, "stack": DEFAULT_FALLBACK[role]}
            )
            continue
        # Only weights and styles with a real file (or a system/external font's
        # plain regular and bold), so nothing shown is a browser-faked bold.
        faces = sorted({(f["weight"], f["style"]) for f in font["files"]})
        if not faces:
            faces = [(400, "normal"), (700, "normal")]
        subsets.update(f["subset"] for f in font["files"] if f["subset"] in SAMPLE_CHARACTERS)
        roles.append(
            {
                "role": role,
                "label": role_label,
                "font": font,
                "stack": stack(role, font),
                "faces": [{"weight": w, "style": s} for w, s in faces],
                "checked": bool(font["files"]),
            }
        )
    type_settings = settings.get("type", {})
    return {
        "roles": roles,
        "type": type_settings,
        "heading_sizes": heading_sizes(type_settings["scale"])
        if "scale" in type_settings
        else None,
        "characters": [
            (name, SAMPLE_CHARACTERS[name]) for name in SAMPLE_CHARACTERS if name in subsets
        ],
    }
