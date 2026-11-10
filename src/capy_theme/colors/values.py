"""A theme's colour values per mode (the base theme with overrides on top), and contrast reports."""

from ..css.shape import shape_values
from .maths import contrast, rating, readable_text, shade
from .names import WITH_CONTENT, overrides


def effective_values(snapshot, scheme):
    """Return a published revision's CSS values for one scheme.

    The base theme's values, with the theme's shape and colour overrides on top. When a
    colour is overridden but its text colour isn't, the text colour is worked
    out so it's readable. When the background (base-100) is overridden but its
    shades or text aren't, those are worked out from it too.
    """
    values = dict(snapshot[f"{scheme}_values"])
    values.update(shape_values(snapshot.get("settings", {})))
    chosen = overrides(snapshot.get("settings", {}), scheme)
    for name, value in chosen.items():
        values[f"--color-{name}"] = value
    for name in WITH_CONTENT:
        if name in chosen and f"{name}-content" not in chosen:
            values[f"--color-{name}-content"] = readable_text(chosen[name])
    if "base-100" in chosen:
        background = chosen["base-100"]
        if "base-200" not in chosen:
            values["--color-base-200"] = shade(background, 1)
        if "base-300" not in chosen:
            values["--color-base-300"] = shade(background, 2)
        if "base-content" not in chosen:
            values["--color-base-content"] = readable_text(background)
    return values


# The colour pairs WCAG ratings are given for: (background, text on it).
CONTRAST_PAIRS = [(name, f"{name}-content") for name in WITH_CONTENT] + [
    ("base-100", "base-content"),
    ("base-200", "base-content"),
    ("base-300", "base-content"),
]


def contrast_report(values):
    """Return one entry per colour pair: background, text, ratio and rating.

    `values` are a scheme's CSS values (from effective_values). Ratings are
    warnings only; they never stop a theme being saved or published.
    """
    report = []
    for background, text in CONTRAST_PAIRS:
        ratio = contrast(values[f"--color-{text}"], values[f"--color-{background}"])
        report.append(
            {
                "background": background,
                "text": text,
                "ratio": round(ratio, 2),
                "rating": rating(ratio),
            }
        )
    return report


def draft_values(theme, scheme):
    """Return the CSS values a theme's draft would publish for one scheme.

    Uses the same merging as publishing. Empty if a base no longer exists.
    """
    snapshot = theme.snapshot()
    if snapshot.get(f"{scheme}_values") is None:
        return {}
    return effective_values(snapshot, scheme)
