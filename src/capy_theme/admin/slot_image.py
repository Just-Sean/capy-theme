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
    """The current image's preview, a choice of this slot's uploads, the current
    image's alt text, and a file input with its own alt text for a new one.

    Its value is {"choice", "upload", "alt", "alt_for", "upload_alt"}. "alt_for" (a
    hidden input) is the image whose alt text the page showed, so an edit only ever
    applies to that image, even if another one is chosen in the same save.
    """

    template_name = "capy_theme/widgets/slot_image.html"
    needs_multipart_form = True  # it has a file input: the form must send files

    class Media:
        css = {"all": ["capy_theme/admin/images.css"]}

    def __init__(self, slot, attrs=None):
        super().__init__(attrs)
        self.slot = slot
        self.choices = []
        self.assets = {}  # this slot's uploads, by id (as text)
        self.empty_text = ""

    def value_from_datadict(self, data, files, name):
        return {
            "choice": data.get(name, ""),
            "upload": files.get(f"{name}_upload"),
            "alt": data.get(f"{name}_alt"),
            "alt_for": data.get(f"{name}_alt_for", ""),
            "upload_alt": data.get(f"{name}_upload_alt", ""),
        }

    def value_omitted_from_data(self, data, files, name):
        return False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        sent = value if isinstance(value, dict) else {"choice": value or ""}
        chosen = str(sent.get("choice") or "")
        current = self.assets.get(chosen)
        # Keep what was typed for this image if the page comes back with errors.
        typed = sent.get("alt") if str(sent.get("alt_for") or "") == chosen else None
        context["widget"].update(
            {
                "options": [(str(v), text, str(v) == chosen) for v, text in self.choices],
                "current": current,
                "empty_text": self.empty_text,
                "alt": typed if typed is not None else (current.alt_text if current else ""),
                "upload_alt": sent.get("upload_alt") or "",
                "alt_max": ALT_MAX,
                "accept": NO_SVG_IMAGE if self.slot in NO_SVG else ANY_IMAGE,
            }
        )
        return context


class SlotImageField(forms.Field):
    """Cleans to {"choice": asset id or None, "clean": a checked new upload or None,
    "upload_alt": its alt text, "alt_for": the image whose alt text was shown (or
    None), "alt": that alt text, or None if it wasn't sent}."""

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
        alt_for = str(value.get("alt_for") or "")
        alt = value.get("alt")
        return {
            "choice": int(choice) if choice else None,
            "clean": clean,
            "upload_alt": _alt(value.get("upload_alt")) or "",
            # Only one of this slot's images; anything else is ignored.
            "alt_for": int(alt_for) if alt_for in self.widget.assets else None,
            "alt": _alt(alt),
        }

    def has_changed(self, initial, data):
        data = data if isinstance(data, dict) else {}
        shown = self.widget.assets.get(str(data.get("alt_for") or ""))
        alt = data.get("alt")
        return bool(
            data.get("upload")
            or str(data.get("choice") or "") != str(initial or "")
            or (shown and alt is not None and alt.strip() != shown.alt_text)
        )


def _alt(text):
    return text.strip()[:ALT_MAX] if text is not None else None
