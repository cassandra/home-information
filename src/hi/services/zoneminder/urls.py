"""
Per-integration URL extension point.

The framework owns lifecycle, configure, sync, and manage URLs for
every integration (see hi/integrations/urls.py). Add
ZoneMinder-specific URLs here when an integration genuinely needs an
endpoint the framework does not provide. URLs added here mount under
``services/zoneminder/``.

Currently no integration-specific endpoints are required.
"""
from django.urls import re_path  # noqa: F401

from . import views  # noqa: F401


urlpatterns = []
