"""The font library in the admin: uploads and Google Fonts import."""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..fonts.google import SUBSETS as GOOGLE_SUBSETS
from ..fonts.google import WEIGHTS as GOOGLE_WEIGHTS
from ..fonts.google import import_family
from ..fonts.library import preview_faces, preview_stack
from ..fonts.models import Font, FontFile
from ..fonts.uploads import SUBSET_CHOICES, prepare


def _int(value, default):
    try:
        return int(value)
    except TypeError, ValueError:
        return default


class FontFileForm(forms.ModelForm):
    """Upload a WOFF2, WOFF, TTF or OTF file. It's checked, converted to WOFF2 and
    optionally trimmed to a character subset. Weight and style are read from the
    font when left blank."""

    weight = forms.IntegerField(
        required=False,
        min_value=100,
        max_value=900,
        help_text="Blank: read from the font. 400 is regular, 700 bold.",
    )
    style = forms.ChoiceField(
        required=False,
        choices=[("", "Read from the font")] + FontFile.STYLES,
    )
    subset = forms.ChoiceField(
        choices=SUBSET_CHOICES,
        initial="latin",
        help_text="Trim the font to these characters (smaller files), or keep all.",
    )
    file = forms.FileField(
        help_text="WOFF2, WOFF, TTF or OTF. Converted to WOFF2.",
        widget=forms.ClearableFileInput(attrs={"accept": ".woff2,.woff,.ttf,.otf"}),
    )

    class Meta:
        model = FontFile
        fields = ["file", "subset", "weight", "style"]

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("file")
        if upload is None or not hasattr(upload, "content_type"):
            # Not a new upload (an existing file): keep what's stored.
            cleaned["weight"] = cleaned.get("weight") or self.instance.weight
            cleaned["style"] = cleaned.get("style") or self.instance.style
            return cleaned
        try:
            prepared = prepare(upload.read(), upload.name, cleaned.get("subset", "all"))
        except ValidationError as error:
            raise ValidationError({"file": error.messages}) from None
        cleaned["file"] = prepared["file"]
        cleaned["weight"] = cleaned.get("weight") or prepared["weight"]
        cleaned["style"] = cleaned.get("style") or prepared["style"]
        self.instance.unicode_range = prepared["unicode_range"]
        return cleaned


class FontFileInline(admin.TabularInline):
    model = FontFile
    form = FontFileForm
    extra = 1
    fields = ["file", "subset", "weight", "style", "unicode_range"]
    readonly_fields = ["unicode_range"]


class GoogleFontForm(forms.Form):
    family = forms.CharField(
        max_length=100, help_text="As written on fonts.google.com, e.g. Lora or Open Sans."
    )
    weights = forms.TypedMultipleChoiceField(
        coerce=int,
        choices=[(w, str(w)) for w in GOOGLE_WEIGHTS],
        initial=[400, 700],
        widget=forms.CheckboxSelectMultiple,
        help_text="Weights the family doesn't have are skipped.",
    )
    italic = forms.BooleanField(required=False, initial=True, label="Italics too")
    subsets = forms.MultipleChoiceField(
        choices=[(s, s) for s in GOOGLE_SUBSETS],
        initial=["latin"],
        widget=forms.CheckboxSelectMultiple,
        label="Character sets",
    )


@admin.register(Font)
class FontAdmin(admin.ModelAdmin):
    """The shared font library. Any theme can use these fonts."""

    change_list_template = "capy_theme/admin/font_change_list.html"

    def get_urls(self):
        return [
            path(
                "import-google/",
                self.admin_site.admin_view(self.import_google_view),
                name="capy_theme_font_import_google",
            ),
            *super().get_urls(),
        ]

    def import_google_view(self, request):
        """Download a Google font once and add it to the library."""
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = GoogleFontForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                font = import_family(
                    form.cleaned_data["family"],
                    weights=form.cleaned_data["weights"],
                    italic=form.cleaned_data["italic"],
                    subsets=form.cleaned_data["subsets"],
                )
            except ValidationError as error:
                form.add_error("family", error)
            else:
                messages.success(
                    request,
                    f"Imported “{font}” ({font.files.count()} files). Pages load it from "
                    "this site, never from Google.",
                )
                return redirect(reverse("admin:capy_theme_font_change", args=[font.pk]))
        context = {
            **self.admin_site.each_context(request),
            "title": "Import a font from Google Fonts",
            "opts": self.opts,
            "form": form,
        }
        return TemplateResponse(request, "capy_theme/admin/import_google_font.html", context)

    list_display = ["family", "preview", "source", "file_count", "created_at"]
    list_filter = ["source"]
    search_fields = ["family"]
    inlines = [FontFileInline]

    readonly_fields = ["preview"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("files")

    @admin.display(description="Files")
    def file_count(self, font):
        return len(font.files.all())

    @admin.display(description="Preview")
    def preview(self, font):
        """A sample of the font (system stacks show in the visitor's own fonts)."""
        if font.pk is None:
            return "Save the font to see a preview."
        return format_html(
            '<style>{}</style><span style="font-family: {}; font-size: 1.25rem;">'
            "The quick brown fox jumps over the lazy dog</span>",
            mark_safe(preview_faces(font)),  # noqa: S308 (built from the font's own data)
            preview_stack(font),
        )
