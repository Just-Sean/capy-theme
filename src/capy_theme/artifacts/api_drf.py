"""The JSON API as a Django REST Framework view, for projects that use DRF.

Only imported when DRF is installed (see api.api_view). drf-spectacular reads the
serializers below to document the response in the project's API docs. They only
describe the response: the view returns get_artifacts() exactly as the plain
Django view does.

The view sets its own authentication, permissions, throttling and renderer, so a
project's DRF defaults (e.g. "login required") don't change this public API.
"""

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import cache_static, catalog_payload, not_modified, theme_payload

try:
    from drf_spectacular.utils import extend_schema
except ImportError:  # drf-spectacular is optional

    def extend_schema(**kwargs):
        return lambda view: view


class ImageVariantSerializer(serializers.Serializer):
    url = serializers.CharField()
    width = serializers.IntegerField()
    format = serializers.CharField(help_text="avif, webp, png or jpeg")


class ImageSerializer(serializers.Serializer):
    url = serializers.CharField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    alt = serializers.CharField(allow_blank=True)
    content_type = serializers.CharField(allow_blank=True)
    variants = ImageVariantSerializer(many=True, help_text="Smaller copies (header logos)")


class FontFileSerializer(serializers.Serializer):
    url = serializers.CharField()
    weight = serializers.IntegerField()
    style = serializers.CharField()
    unicode_range = serializers.CharField(allow_blank=True)


class FontSerializer(serializers.Serializer):
    family = serializers.CharField()
    stack = serializers.CharField(help_text="A CSS font-family value")
    source = serializers.CharField()
    stylesheet = serializers.CharField(allow_blank=True)
    files = FontFileSerializer(many=True)


class ArtifactsSerializer(serializers.Serializer):
    theme = serializers.DictField(help_text="name, slug, scheme and published revision number")
    branding = serializers.DictField(child=serializers.CharField(allow_blank=True))
    colors = serializers.DictField(child=serializers.CharField())
    colors_hex = serializers.DictField(child=serializers.CharField())
    fonts = serializers.DictField(child=FontSerializer(), help_text="Keyed by role")
    shape = serializers.DictField(child=serializers.CharField())
    type = serializers.DictField(child=serializers.FloatField())
    logos = serializers.DictField(child=ImageSerializer(allow_null=True), help_text="Keyed by slot")
    icons = serializers.DictField(child=serializers.CharField(), help_text="File name: URL")
    sharing_image = serializers.DictField(allow_null=True)
    backgrounds = serializers.DictField(child=serializers.CharField(allow_null=True))
    stylesheet_url = serializers.CharField()


class CatalogEntrySerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    scheme = serializers.CharField(help_text='"light" or "dark"')
    default = serializers.BooleanField(help_text="The domain's default theme for its scheme")
    swatch = serializers.CharField(help_text="Primary color, #rrggbb")
    background = serializers.CharField(help_text="base-100 color, #rrggbb")
    assets_url = serializers.CharField()
    stylesheet_url = serializers.CharField()


class ThemeCatalogAPIView(APIView):
    """The available themes: slug, name, scheme, which is default, and a swatch."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    renderer_classes = [JSONRenderer]

    @extend_schema(
        responses={200: CatalogEntrySerializer(many=True), 304: None},
        summary="Available themes",
        description="The themes offered to visitors, plus the default. Send the ETag "
        "back in If-None-Match to get 304 until a theme changes.",
    )
    def get(self, request):
        data, etag = catalog_payload(request)
        if not_modified(request, etag):
            response = Response(status=304)
        else:
            response = Response(data)
        if etag:
            response["ETag"] = etag
        return cache_static(response)


class ThemeAssetsAPIView(APIView):
    """One theme's colors, fonts, shape, logos, icons and images, by slug."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    renderer_classes = [JSONRenderer]

    @extend_schema(
        responses={200: ArtifactsSerializer, 304: None, 404: None},
        summary="A theme's assets",
        description="A published theme's values and asset URLs (absolute), by slug (or "
        '"default"). Send the ETag back in If-None-Match to get 304.',
    )
    def get(self, request, slug):
        data, etag = theme_payload(request, slug)
        if data is None:
            response = Response({"error": "No such theme."}, status=404)
        elif not_modified(request, etag):
            response = Response(status=304)
        else:
            response = Response(data)
        if etag:
            response["ETag"] = etag
        return cache_static(response)
