"""Per-integration URL extension point.

Mounts under ``services/paperless/`` via the framework's
auto-discovery (see hi/integrations/urls.py). One route: a thumbnail
proxy used by the EXTERNAL_REFERENCE picker so browser-rendered
<img> tags can fetch paperless thumbnails through HI's session
instead of requiring the upstream paperless API token.
"""
from django.urls import path

from .views import ThumbnailProxyView


urlpatterns = [
    path(
        'documents/<int:document_id>/thumb/',
        ThumbnailProxyView.as_view(),
        name = 'paperless_thumbnail',
    ),
]
