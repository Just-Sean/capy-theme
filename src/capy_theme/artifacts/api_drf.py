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

from .api import CACHE_CONTROL, not_modified, payload

try:
    from drf_spectacular.utils import extend_schema
except ImportError:  # drf-spectacular is optional

    def extend_schema(**kwargs):
        return lambda view: view


def _modes(child):
    return serializers.DictField(child=child, help_text='Keyed by mode: "light" and "dark".')


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


class LogoModesSerializer(serializers.Serializer):
    light = ImageSerializer(allow_null=True)
    dark = ImageSerializer(allow_null=True)


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


class BackgroundSerializer(serializers.Serializer):
    light = serializers.CharField(allow_null=True)
    dark = serializers.CharField(allow_null=True)


class ArtifactsSerializer(serializers.Serializer):
    theme = serializers.DictField(help_text="name, slug and published revision number")
    branding = serializers.DictField(child=serializers.CharField(allow_blank=True))
    colors = _modes(serializers.DictField(child=serializers.CharField()))
    colors_hex = _modes(serializers.DictField(child=serializers.CharField()))
    fonts = serializers.DictField(child=FontSerializer(), help_text="Keyed by role")
    shape = _modes(serializers.DictField(child=serializers.CharField()))
    type = serializers.DictField(child=serializers.FloatField())
    logos = serializers.DictField(child=LogoModesSerializer(), help_text="Keyed by slot")
    icons = serializers.DictField(child=serializers.CharField(), help_text="File name: URL")
    sharing_image = serializers.DictField(allow_null=True)
    backgrounds = serializers.DictField(child=BackgroundSerializer())
    mode = serializers.DictField(help_text="default and visitors_can_switch")
    stylesheet_url = serializers.CharField()


class ThemeAPIView(APIView):
    """The active theme's colours, fonts, shape, logos, icons and images."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    renderer_classes = [JSONRenderer]

    @extend_schema(
        responses={200: ArtifactsSerializer, 304: None, 404: None},
        summary="The active theme",
        description="The published theme's values and asset URLs (absolute). Send the "
        "ETag back in If-None-Match to get 304 until the theme changes.",
    )
    def get(self, request):
        data, etag = payload(request)
        if data is None:
            response = Response({"error": "No theme is published."}, status=404)
        elif not_modified(request, etag):
            response = Response(status=304)
        else:
            response = Response(data)
        if etag:
            response["ETag"] = etag
        response["Cache-Control"] = CACHE_CONTROL
        return response
