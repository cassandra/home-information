"""Frigate API endpoints (simulator-side).

Scaffolding stub — feature work fills in the routes that the HI
Frigate integration will hit:

- ``GET /api/events`` — list events
- ``GET /api/events/<id>`` — single event detail
- ``GET /api/events/<id>/snapshot.jpg`` — event snapshot
- ``GET /api/events/<id>/clip.mp4`` — event clip
- ``GET /api/<camera>/latest.jpg`` — live snapshot
- ``GET /api/config`` — Frigate config (camera list lives here)
- ``GET /api/stats`` — Frigate stats
"""
from django.urls import path  # noqa: F401


urlpatterns: list = []
