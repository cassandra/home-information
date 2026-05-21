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

    path( 'events',
          views.EventsListView.as_view(),
          name = 'frigate_api_events' ),

    # ``events/<id>/snapshot.jpg`` and ``events/<id>/clip.mp4`` both
    # precede the generic ``events/<id>`` route so the trailing path
    # segment is matched before the JSON-detail catch-all.
    path( 'events/<str:event_id>/snapshot.jpg',
          views.EventSnapshotJpegView.as_view(),
          name = 'frigate_api_event_snapshot' ),

    path( 'events/<str:event_id>/clip.mp4',
          views.EventClipMp4View.as_view(),
          name = 'frigate_api_event_clip' ),

    path( 'events/<str:event_id>',
          views.EventDetailView.as_view(),
          name = 'frigate_api_event_detail' ),

    path( '<str:camera_name>/latest.jpg',
          views.CameraLatestJpegView.as_view(),
          name = 'frigate_api_camera_snapshot' ),
]
