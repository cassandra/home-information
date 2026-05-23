"""
Per-integration URL extension point.

The framework owns lifecycle, configure, sync, and manage URLs for
every integration (see hi/integrations/urls.py). Add HomeBox-specific
URLs here when an integration genuinely needs an endpoint the
framework does not provide. URLs added here mount under
``services/homebox/``.

The attachment proxy endpoint serves HomeBox attachments and
thumbnails to the browser. HomeBox requires bearer-token auth so the
browser cannot fetch them directly; the proxy uses the server-side
stored token and streams the bytes through.
"""
from django.urls import re_path

from . import views  # noqa: F401
from .connector.proxy_views import HomeBoxAttachmentProxyView


urlpatterns = [
    re_path(
        r'^proxy/attachment/(?P<entity_id>\d+)/(?P<attachment_id>[^/]+)/?$',
        HomeBoxAttachmentProxyView.as_view(),
        name='homebox_attachment_proxy',
    ),
]
