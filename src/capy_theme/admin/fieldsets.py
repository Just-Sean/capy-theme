"""How the theme admin page is laid out: its sections and their fields."""

from ..css.shape import SHAPE_NAMES
from ..css.typography import TYPE_SETTINGS
from ..fonts.library import ROLES
from ..images.logos import HEIGHTS, LOGO_SLOTS
from .form_colors import color_fieldsets
from .form_images import CHOOSABLE, image_field_name

MORE_LOGOS = "More logo versions (optional)"

THEME_FIELDSETS = [
    (
        "Name",
        {
            "fields": ["name", "slug"],
            "description": "The name and slug are labels in the admin; visitors never see "
            "them. Tip: <strong>Edit live</strong> (top right) changes this theme on the "
            "page itself and shows every change as you make it.",
        },
    ),
    ("Publishing", {"fields": ["publish_status"]}),
    (
        "Base themes",
        {
            "fields": ["light_base", "dark_base"],
            "description": "Every theme starts from two of daisyUI's built-in themes. "
            "Anything you don't change below comes from them.",
        },
    ),
    ("Branding", {"fields": ["site_name", "tagline", "logo_alt"]}),
    (
        "Icon",
        {
            "fields": [
                "image_icon_light",
                "image_icon_dark",
                "icon_background",
                "icon_padding",
            ],
            "description": "Upload a new image or pick an earlier one right here. The icons "
            "are made from it when you publish.",
        },
    ),
    (
        "Logos",
        {
            "fields": [
                image_field_name("logo_main", "light"),
                image_field_name("logo_main", "dark"),
                *[f"logo_{name}" for name in HEIGHTS],
            ],
            "description": "Upload a new image or pick an earlier one right here, then save. "
            "Visitors see it once you publish. Most sites only need the main logo; other "
            "versions are under More logo versions.",
        },
    ),
    (
        MORE_LOGOS,
        {
            "fields": [
                image_field_name(slot, mode)
                for slot in LOGO_SLOTS
                if slot != "logo_main"
                for mode in CHOOSABLE[slot]
            ],
            "description": "Optional versions of your logo for particular places. Each one "
            "says what it's for. Any you leave empty use the main logo, so you only need "
            "these if your logo should look different there.",
        },
    ),
    ("Fonts", {"fields": [f"font_{role}" for role in ROLES]}),
    ("Type scale", {"fields": [f"type_{name}" for name in TYPE_SETTINGS]}),
    *color_fieldsets(),
    ("Contrast", {"fields": ["contrast_table"], "classes": ["collapse"]}),
    (
        "Shape and effects",
        {"fields": [f"shape_{name}" for name in SHAPE_NAMES], "classes": ["collapse"]},
    ),
    ("Mode", {"fields": ["default_mode", "visitors_can_switch"]}),
    (
        "Visitors",
        {
            "fields": ["offered_to_visitors"],
            "description": "Themes offered to visitors appear in {% theme_picker %} once "
            "they're published. Visitors can only pick offered themes.",
        },
    ),
    (
        "Backgrounds",
        {
            "fields": [
                image_field_name(slot, mode)
                for slot in ("background_login", "background_pattern")
                for mode in ("light", "dark")
            ],
            "classes": ["collapse"],
            "description": "Optional. Upload a new image or pick an earlier one right here. "
            "Each one says where it shows.",
        },
    ),
    (
        "Sharing image",
        {
            "fields": ["image_social_light"],
            "classes": ["collapse"],
            "description": "Optional. Upload a new image or pick an earlier one right here. "
            "capy-theme makes it available (see Theme artifacts in the README); the "
            "project's own templates or another module add the preview tags.",
        },
    ),
    (
        "Custom CSS",
        {
            "fields": ["custom_css", "custom_css_enabled"],
            "classes": ["collapse"],
            "description": "Only shown to users with the “Can edit a theme's custom CSS” "
            "permission. Published with the theme and served as its own file.",
        },
    ),
    (
        "Advanced",
        {
            "fields": ["settings_json", "public_id", "created_at", "updated_at"],
            "classes": ["collapse"],
            "description": "The stored settings, read-only: they're edited through the "
            "sections above or the live editor.",
        },
    ),
]

# Every section can be folded, and starts folded. Django shows a section with errors
# unfolded.
for _name, _options in THEME_FIELDSETS:
    _options["classes"] = sorted({*_options.get("classes", []), "collapse"})
