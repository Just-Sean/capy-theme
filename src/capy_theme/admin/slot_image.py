"""One image slot (and mode) on the theme page: its current image, earlier uploads,
a new upload and the alt text, all in one place (#271)."""

from django import forms
from django.core.exceptions import ValidationError

from ..images.assets import ALT_MAX
from ..images.slots import NO_SVG
from ..images.uploads import prepare_upload

ANY_IMAGE = "image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
NO_SVG_IMAGE = "image/png,image/jpeg,image/webp,image/gif"


class SlotImageWidget(forms.Widget):
    """The current image's preview, a choice of this slot's uploads, a file input
    for a new one and its alt text. Its value is {"choice", "upload", "alt"}."""

    template_name = "capy_theme/widgets/slot_image.html"
    needs_multipart_form = True  # it has a file input: the form must send files

    class Media:
        css = {"all": ["capy_theme/admin/images.css"]}

    def __init__(self, slot, attrs=None):
        super().__init__(attrs)
        self.slot = slot
        self.choices = []
        self.assets = {}  # this slot's uploads, by id
        self.empty_text = ""

    def value_from_datadict(self, data, files, name):
        return {
            "choice": data.get(name, ""),
            "upload": files.get(f"{name}_upload"),
            "alt": data.get(f"{name}_alt"),
        }

    def value_omitted_from_data(self, data, files, name):
        return False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        chosen = value.get("choice", "") if isinstance(value, dict) else (value or "")
        current = self.assets.get(str(chosen))
        alt = value.get("alt") if isinstance(value, dict) else None
        context["widget"].update(
            {
                "options": [(str(v), text, str(v) == str(chosen)) for v, text in self.choices],
                "current": current,
                "empty_text": self.empty_text,
                "alt": current.alt_text if alt is None and current else (alt or ""),
                "accept": NO_SVG_IMAGE if self.slot in NO_SVG else ANY_IMAGE,
            }
        )
        return context


class SlotImageField(forms.Field):
    """Cleans to {"choice": asset id or None, "clean": a checked new upload or None,
    "alt": the alt text, or None if it wasn't sent}."""

    def __init__(self, slot, mode, **kwargs):
        self.slot, self.mode = slot, mode
        kwargs.setdefault("required", False)
        super().__init__(widget=SlotImageWidget(slot), **kwargs)

    def clean(self, value):
        value = value if isinstance(value, dict) else {"choice": value}
        choice = str(value.get("choice") or "")
        if choice and choice not in {str(v) for v, _text in self.widget.choices if v}:
            raise ValidationError("Choose one of this slot's images.")
        clean = None
        upload = value.get("upload")
        if upload:
            clean = prepare_upload(upload, self.slot)  # raises ValidationError
        alt = value.get("alt")
        return {
            "choice": int(choice) if choice else None,
            "clean": clean,
            "alt": alt.strip()[:ALT_MAX] if alt is not None else None,
        }

    def has_changed(self, initial, data):
        data = data if isinstance(data, dict) else {}
        current = self.widget.assets.get(str(initial or ""))
        alt = data.get("alt")
        return bool(
            data.get("upload")
            or str(data.get("choice") or "") != str(initial or "")
            or (current and alt is not None and alt.strip() != current.alt_text)
        )
