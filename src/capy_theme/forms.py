"""Form fields shared by the admin (and later the editor)."""

from django import forms
from django.core.exceptions import ValidationError

from .colors import to_hex, to_oklch


class ColorWidget(forms.TextInput):
    """A text box for any colour format, with the browser's colour picker beside it.

    Picking a colour writes its hex value into the text box; typing a value
    moves the picker to match (static/capy_theme/admin/color_input.js).
    """

    template_name = "capy_theme/widgets/color.html"

    class Media:
        js = ["capy_theme/admin/color_input.js"]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        shown = value or self.attrs.get("placeholder") or ""
        try:
            context["widget"]["picker_value"] = to_hex(shown, alpha=False) if shown else "#000000"
        except ValueError:
            context["widget"]["picker_value"] = "#000000"
        return context


class ColorField(forms.CharField):
    """Accepts hex, rgb(), hsl(), oklch() or a colour name; cleans to OKLCH text."""

    widget = ColorWidget
    default_error_messages = {
        "invalid": "Enter a colour, e.g. #3b82f6, rgb(59 130 246) or oklch(62% 0.19 260).",
    }

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return ""
        try:
            return to_oklch(value)
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid") from None
