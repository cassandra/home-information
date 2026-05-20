"""Frigate API endpoints (simulator-side).

Mirrors the shape of Frigate's real HTTP API. Routes are added in
parallel with the HI client's per-endpoint support — at any given
point only the endpoints HI talks to need to exist.
"""
from django.urls import path

from . import views


urlpatterns = [

    path( 'config',
          views.ConfigView.as_view(),
          name = 'frigate_api_config' ),
]
