"""Respecting visitors' device settings: reduce motion and more contrast.

daisyUI only honors "reduce motion" in a few components and has nothing for
"more contrast", so the theme stylesheet adds both for the whole page.
"""


def accessibility_css():
    """CSS for prefers-reduced-motion and prefers-contrast."""
    return "\n".join(
        [
            # Reduce motion: animations and transitions finish at once, and
            # scrolling jumps instead of gliding. Not 0s, so animationend and
            # transitionend events still fire for scripts that wait for them.
            "@media (prefers-reduced-motion: reduce) {",
            "  *, *::before, *::after {",
            "    animation-duration: 0.01ms !important;",
            "    animation-iteration-count: 1 !important;",
            "    transition-duration: 0.01ms !important;",
            "    transition-delay: 0s !important;",
            "    scroll-behavior: auto !important;",
            "  }",
            "}",
            # More contrast: no noise texture or depth shading (they blur edges),
            # thicker borders and a thicker focus outline. Colors stay the theme's.
            "@media (prefers-contrast: more) {",
            "  :root, [data-theme] {",
            "    --noise: 0 !important;",
            "    --depth: 0 !important;",
            "    --border: 2px !important;",
            "  }",
            "  :focus-visible {",
            "    outline-width: 3px;",
            "  }",
            "}",
        ]
    )
