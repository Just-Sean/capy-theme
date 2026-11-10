import json

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .active import NotPublished, activate, get_active_theme
from .catalogue import builtin_values, get_builtin_themes
from .colors import (
    COLOR_GROUPS,
    COLOR_NAMES,
    SCHEMES,
    contrast_report,
    draft_values,
    label,
)
from .editor import can_edit
from .font_files import SUBSET_CHOICES, prepare
from .fonts import ROLES, preview_faces, preview_stack
from .forms import ColorField
from .google_fonts import SUBSETS as GOOGLE_SUBSETS
from .google_fonts import WEIGHTS as GOOGLE_WEIGHTS
from .google_fonts import import_family
from .history import compare as compare_revisions
from .history import restore as restore_revision
from .models import Font, FontFile, Theme, ThemeRevision
from .publishing import NothingToPublish, publish
from .shape import EFFECTS, SHAPE_NAMES, SIZES
from .stylesheet import stylesheet_url


def _base_choices(scheme):
    return [(theme.name, theme.name) for theme in get_builtin_themes() if theme.scheme == scheme]


class ThemeForm(forms.ModelForm):
    """The theme edit form.

    Only light themes are offered as the light base and dark themes as the dark
    base. Values stored in `settings` (site name, tagline, logo alt text) get
    their own fields here and are written back into `settings` on save.
    """

    light_base = forms.ChoiceField()
    dark_base = forms.ChoiceField()
    site_name = forms.CharField(
        required=False,
        max_length=100,
        help_text="Shown in headers, and instead of the logo if there's none.",
    )
    tagline = forms.CharField(
        required=False, max_length=200, help_text="A short line describing the site."
    )
    logo_alt = forms.CharField(
        required=False,
        max_length=200,
        label="Logo alt text",
        help_text="Describes the logo for screen readers. Leave blank to use the site name.",
    )

    default_mode = forms.ChoiceField(
        choices=[
            ("auto", "Auto: follow the visitor's device"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        initial="auto",
        required=False,  # missing means "auto"
        help_text="The colour mode pages use until a visitor picks one.",
    )
    visitors_can_switch = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Lets visitors choose light, dark or auto with {% theme_mode_toggle %}.",
    )

    # Form fields stored as keys in Theme.settings.
    SETTINGS_FIELDS = ["site_name", "tagline", "logo_alt"]

    class Meta:
        model = Theme
        fields = ["name", "slug", "light_base", "dark_base", "logo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            self.fields[field].choices = _base_choices(scheme)
            self.fields[field].help_text = Theme._meta.get_field(field).help_text
            self.fields[field].initial = Theme._meta.get_field(field).default
        for field in self.SETTINGS_FIELDS:
            self.fields[field].initial = self.instance.settings.get(field, "")
        colors = self.instance.settings.get("colors", {})
        for scheme in SCHEMES:
            base = builtin_values(getattr(self.instance, f"{scheme}_base")) or {}
            for name in COLOR_NAMES:
                field = self.fields[color_field_name(scheme, name)]
                field.initial = colors.get(scheme, {}).get(name, "")
                field.widget.attrs["placeholder"] = base.get(f"--color-{name}", "")
        font_choices = [("", "Default")] + [(str(f.pk), str(f)) for f in Font.objects.all()]
        chosen_fonts = self.instance.settings.get("fonts", {})
        for role in ROLES:
            self.fields[f"font_{role}"].choices = font_choices
            self.fields[f"font_{role}"].initial = str(chosen_fonts.get(role, ""))
        shape = self.instance.settings.get("shape", {})
        base = builtin_values(self.instance.light_base) or {}
        for name, (variable, unit, *_rest) in SIZES.items():
            field = self.fields[f"shape_{name}"]
            field.initial = shape.get(name)
            field.widget.attrs["placeholder"] = base.get(variable, "").removesuffix(unit)
            field.widget.attrs["step"] = "any"
        for name in EFFECTS:
            if name in shape:
                self.fields[f"shape_{name}"].initial = "on" if shape[name] else "off"
        if self.instance.pk:
            self._add_contrast_ratings()
        self.fields["default_mode"].initial = self.instance.settings.get("default_mode", "auto")
        self.fields["visitors_can_switch"].initial = self.instance.settings.get(
            "visitors_can_switch", True
        )

    def _add_contrast_ratings(self):
        """Show each colour's WCAG contrast rating (from the saved draft) in its help text."""
        for scheme in SCHEMES:
            values = draft_values(self.instance, scheme)
            if not values:
                continue
            for entry in contrast_report(values):
                note = _rating_note(entry)
                for name in (entry["background"], entry["text"]):
                    field = self.fields[color_field_name(scheme, name)]
                    field.help_text = f"{field.help_text} {note}"

    def clean(self):
        cleaned = super().clean()
        settings = dict(self.instance.settings)
        for field in self.SETTINGS_FIELDS:
            value = cleaned.get(field, "").strip()
            if value:
                settings[field] = value
            else:
                settings.pop(field, None)
        # Mode settings are stored only when they differ from the defaults
        # ("auto" and visitors can switch), like the other optional settings.
        if cleaned.get("default_mode") in ("light", "dark"):
            settings["default_mode"] = cleaned["default_mode"]
        else:
            settings.pop("default_mode", None)
        if cleaned.get("visitors_can_switch", True):
            settings.pop("visitors_can_switch", None)
        else:
            settings["visitors_can_switch"] = False
        colors = {}
        for scheme in SCHEMES:
            chosen = {}
            for name in COLOR_NAMES:
                value = (cleaned.get(color_field_name(scheme, name)) or "").strip()
                if value:
                    chosen[name] = value
            if chosen:
                colors[scheme] = chosen
        if colors:
            settings["colors"] = colors
        else:
            settings.pop("colors", None)
        fonts = {
            role: int(cleaned[f"font_{role}"]) for role in ROLES if cleaned.get(f"font_{role}")
        }
        if fonts:
            settings["fonts"] = fonts
        else:
            settings.pop("fonts", None)
        shape = {}
        for name in SIZES:
            value = cleaned.get(f"shape_{name}")
            if value is not None:
                shape[name] = float(value)
        for name in EFFECTS:
            choice = cleaned.get(f"shape_{name}")
            if choice in ("on", "off"):
                shape[name] = choice == "on"
        if shape:
            settings["shape"] = shape
        else:
            settings.pop("shape", None)
        self.instance.settings = settings
        return cleaned


def _pair(entry):
    return f"{label(entry['background'])} / {label(entry['text'])}"


def _rating_note(entry):
    words = {"AAA": "passes AAA", "AA": "passes AA", "fail": "⚠ fails AA, hard to read"}
    return f"Contrast {_pair(entry)}: {entry['ratio']}:1, {words[entry['rating']]}."


def color_field_name(scheme, name):
    """The form field for one colour override, e.g. color_light_base_100."""
    return f"color_{scheme}_{name.replace('-', '_')}"


for _scheme in SCHEMES:
    for _name in COLOR_NAMES:
        # Added to both, so the admin's own copy of the form (built with
        # modelform_factory) knows these fields too.
        ThemeForm.base_fields[color_field_name(_scheme, _name)] = ThemeForm.declared_fields[
            color_field_name(_scheme, _name)
        ] = ColorField(
            required=False,
            label=label(_name),
            help_text="Any colour format (hex, rgb, hsl, oklch); saved as OKLCH. "
            "Leave blank to use the base theme's colour (shown greyed out).",
        )


for _name, (_variable, _unit, _low, _high, _label, _help) in SIZES.items():
    ThemeForm.base_fields[f"shape_{_name}"] = ThemeForm.declared_fields[f"shape_{_name}"] = (
        forms.DecimalField(
            required=False,
            min_value=_low,
            max_value=_high,
            decimal_places=4,
            label=f"{_label} ({_unit})",
            help_text=f"{_help} Leave blank to use the base theme's value (shown greyed out).",
        )
    )
for _name, (_variable, _label, _help) in EFFECTS.items():
    ThemeForm.base_fields[f"shape_{_name}"] = ThemeForm.declared_fields[f"shape_{_name}"] = (
        forms.ChoiceField(
            required=False,
            choices=[("", "From the base theme"), ("on", "On"), ("off", "Off")],
            label=_label,
            help_text=_help,
        )
    )


for _role, _label in ROLES.items():
    ThemeForm.base_fields[f"font_{_role}"] = ThemeForm.declared_fields[f"font_{_role}"] = (
        forms.ChoiceField(
            required=False,
            label=_label,
            help_text="Blank uses the project's default font. Add fonts under Capy Theme → Fonts.",
        )
    )


def color_fieldsets():
    """Admin fieldsets for the colour overrides: Basic, Advanced, Expert, per mode."""
    sets = []
    for scheme in SCHEMES:
        for group, names in COLOR_GROUPS.items():
            classes = [] if group == "Basic" else ["collapse"]
            sets.append(
                (
                    f"{scheme.capitalize()} colours: {group}",
                    {
                        "fields": [color_field_name(scheme, n) for n in names],
                        "classes": classes,
                    },
                )
            )
    return sets


def edit_live_url(theme_id):
    """Where "Edit live" opens the editor: the showcase, or the home page if it's off."""
    if getattr(settings, "CAPY_THEME_SHOWCASE", "staff") != "off":
        return f"{reverse('capy_theme:showcase')}?edit={theme_id}"
    return f"/?edit={theme_id}"


class PublishForm(forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "cols": 60}),
        help_text="Optional: what changed or why, for the history.",
    )


class ThemeRevisionInline(admin.TabularInline):
    """The theme's published revisions. They can be viewed, never edited or deleted."""

    model = ThemeRevision
    fields = ["number", "published_at", "published_by", "note", "is_live"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = False
    verbose_name = "published revision"
    verbose_name_plural = "Published revisions"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="Live")
    def is_live(self, revision):
        return revision.theme.live_revision_id == revision.pk


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    form = ThemeForm
    change_form_template = "capy_theme/admin/theme_change_form.html"
    list_display = [
        "name",
        "slug",
        "light_base",
        "dark_base",
        "is_active",
        "live_revision_number",
        "unpublished_changes",
        "base_changed_in_daisyui",
        "updated_at",
    ]
    actions = ["activate_theme"]
    list_filter = ["light_base", "dark_base"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = [
        "publish_status",
        "contrast_table",
        "settings_json",
        "public_id",
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (
            None,
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
        ("Branding", {"fields": ["site_name", "tagline", "logo", "logo_alt"]}),
        ("Fonts", {"fields": [f"font_{role}" for role in ROLES]}),
        *color_fieldsets(),
        ("Contrast", {"fields": ["contrast_table"], "classes": ["collapse"]}),
        (
            "Shape and effects",
            {"fields": [f"shape_{name}" for name in SHAPE_NAMES], "classes": ["collapse"]},
        ),
        ("Mode", {"fields": ["default_mode", "visitors_can_switch"]}),
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
    inlines = [ThemeRevisionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("live_revision")

    @admin.display(description="WCAG contrast (saved draft)")
    def contrast_table(self, theme):
        """Every colour pair's contrast rating, for light and dark. Warnings only."""
        if theme.pk is None:
            return "Save the theme to see its contrast ratings."
        rows = []
        for scheme in SCHEMES:
            values = draft_values(theme, scheme)
            if not values:
                continue
            for entry in contrast_report(values):
                rows.append(
                    format_html(
                        "<tr><td>{}</td><td>{}</td><td>{}:1</td><td>{}</td></tr>",
                        scheme.capitalize(),
                        _pair(entry),
                        entry["ratio"],
                        "⚠ fails AA" if entry["rating"] == "fail" else entry["rating"],
                    )
                )
        return format_html(
            "<table><thead><tr><th>Mode</th><th>Pair</th><th>Ratio</th><th>Rating</th></tr>"
            "</thead><tbody>{}</tbody></table>"
            "<p>AA needs 4.5:1 and AAA 7:1 for normal text. These are warnings: saving and "
            "publishing still work.</p>",
            format_html_join("", "{}", ((row,) for row in rows)),
        )

    @admin.display(description="Stored settings")
    def settings_json(self, theme):
        """The draft's `settings` as JSON, read-only. Edited through the fields above."""
        return format_html("<pre>{}</pre>", json.dumps(theme.settings, indent=2, sort_keys=True))

    @admin.display(boolean=True, description="Active")
    def is_active(self, theme):
        active = get_active_theme()
        return active is not None and active.pk == theme.pk

    def has_publish_permission(self, request, obj=None):
        """Publishing, activating and (later) restoring need the publish_theme permission."""
        return request.user.has_perm("capy_theme.publish_theme")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_publish": self.has_publish_permission(request),
            "edit_live_url": edit_live_url(object_id) if can_edit(request.user) else None,
        }
        return super().change_view(request, object_id, form_url, extra_context)

    # Shown in the actions menu only to users with the publish_theme permission.
    @admin.action(
        description="Activate the selected theme (make it the site's theme)",
        permissions=["publish"],
    )
    def activate_theme(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, "Select exactly one theme to activate.")
            return
        theme = queryset.select_related("live_revision").get()
        try:
            activate(theme)
        except NotPublished as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"“{theme}” is now the active theme.")

    @admin.display(description="Live revision", ordering="live_revision__number")
    def live_revision_number(self, theme):
        return theme.live_revision.number if theme.live_revision else "—"

    @admin.display(boolean=True, description="Unpublished changes")
    def unpublished_changes(self, theme):
        return theme.has_unpublished_changes

    @admin.display(boolean=True, description="Base changed in daisyUI")
    def base_changed_in_daisyui(self, theme):
        return bool(theme.base_changes())

    @admin.display(description="Status")
    def publish_status(self, theme):
        if theme.pk is None:
            return "Not saved yet. Save the theme, then publish it."
        live = theme.live_revision
        if live is None:
            return "Never published. Pages won't use this theme until it's published."
        changes = (
            "The draft has unpublished changes."
            if theme.has_unpublished_changes
            else "The draft matches the live revision."
        )
        status = format_html(
            'Live: revision {} (published {} by {}). {} <a href="{}" target="_blank">'
            "View its stylesheet</a>",
            live.number,
            live.published_at.strftime("%Y-%m-%d %H:%M"),
            live.published_by or "unknown",
            changes,
            stylesheet_url(live),
        )
        for note in theme.base_changes():
            status += format_html('<p class="errornote">{}</p>', note)
        return status

    # The Publish page

    def get_urls(self):
        return [
            path(
                "<path:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="capy_theme_theme_publish",
            ),
            path(
                "<path:object_id>/revisions/",
                self.admin_site.admin_view(self.revisions_view),
                name="capy_theme_theme_revisions",
            ),
            path(
                "<path:object_id>/revisions/<int:number>/restore/",
                self.admin_site.admin_view(self.restore_view),
                name="capy_theme_theme_restore",
            ),
            *super().get_urls(),
        ]

    def publish_view(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_publish_permission(request, theme):
            raise PermissionDenied
        change_url = reverse("admin:capy_theme_theme_change", args=[theme.pk])

        form = PublishForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                revision = publish(theme, user=request.user, note=form.cleaned_data["note"])
            except NothingToPublish as error:
                messages.warning(request, str(error))
            except ValidationError as error:
                messages.error(request, "Can't publish: " + " ".join(error.messages))
            except IntegrityError:
                # Someone else published this theme at the same moment and took
                # the next revision number. Nothing was saved for this request.
                messages.warning(
                    request,
                    "Someone else just published this theme, so yours wasn't saved. "
                    "Check the live revision below, then publish again if needed.",
                )
            else:
                messages.success(request, f"Published “{theme}” as revision {revision.number}.")
            return redirect(change_url)

        context = {
            **self.admin_site.each_context(request),
            "title": f"Publish “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "form": form,
            "change_url": change_url,
            "has_changes": theme.has_unpublished_changes,
        }
        return TemplateResponse(request, "capy_theme/admin/publish_theme.html", context)

    # Revisions: list, compare and restore

    def revisions_view(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_view_or_change_permission(request, theme):
            raise PermissionDenied
        revisions = list(theme.revisions.select_related("published_by"))
        numbers = [r.number for r in revisions]
        older = _int(request.GET.get("a"), numbers[1] if len(numbers) > 1 else None)
        newer = _int(request.GET.get("b"), numbers[0] if numbers else None)
        by_number = {r.number: r for r in revisions}
        differences = None
        if older in by_number and newer in by_number:
            differences = compare_revisions(by_number[older], by_number[newer])
        context = {
            **self.admin_site.each_context(request),
            "title": f"Revisions of “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "revisions": revisions,
            "older": older,
            "newer": newer,
            "differences": differences,
            "can_restore": self.has_publish_permission(request, theme),
            "change_url": reverse("admin:capy_theme_theme_change", args=[theme.pk]),
        }
        return TemplateResponse(request, "capy_theme/admin/revisions.html", context)

    def restore_view(self, request, object_id, number):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_publish_permission(request, theme):
            raise PermissionDenied
        revision = get_object_or_404(theme.revisions, number=number)
        revisions_url = reverse("admin:capy_theme_theme_revisions", args=[theme.pk])
        if request.method == "POST":
            try:
                new = restore_revision(theme, revision, user=request.user)
            except NothingToPublish:
                messages.warning(request, f"Revision {number} is already what's live.")
            except ValidationError as error:
                messages.error(request, "Can't restore: " + " ".join(error.messages))
            except IntegrityError:
                messages.warning(
                    request, "Someone else just published this theme. Check, then try again."
                )
            else:
                messages.success(
                    request, f"Restored revision {number}. It's live as revision {new.number}."
                )
            return redirect(revisions_url)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Restore revision {number} of “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "revision": revision,
            "differences": compare_revisions(theme.live_revision, revision)
            if theme.live_revision
            else None,
            "revisions_url": revisions_url,
        }
        return TemplateResponse(request, "capy_theme/admin/restore.html", context)


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
