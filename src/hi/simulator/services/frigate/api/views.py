"""Frigate-shape HTTP API views (simulator-side).

Each view returns the JSON shape a real Frigate instance would
respond with, so HI's ``FrigateClient`` can talk to the simulator
without any client-side branching.
"""
import logging

from django.http import JsonResponse
from django.views.generic import View

from hi.simulator.services.frigate.simulator import FrigateSimulator

logger = logging.getLogger(__name__)


class ConfigView( View ):
    """``GET /api/config`` — Frigate's effective configuration.

    Real Frigate returns a large nested document; HI's integration
    only cares about the ``cameras`` map (camera names are the keys).
    We emit the minimum shape the client needs plus a token of
    per-camera info so the response is recognizable as Frigate JSON.
    """

    def get(self, request, *args, **kwargs):
        try:
            simulator = FrigateSimulator()
            cameras = {}
            for sim_camera in simulator.get_sim_cameras():
                cameras[ sim_camera.camera_name ] = {
                    'name': sim_camera.camera_name,
                    'friendly_name': sim_camera.display_name,
                    'enabled': True,
                }
            return JsonResponse( { 'cameras': cameras } )
        except Exception:
            logger.exception( 'Problem processing Frigate /api/config request.' )
            return JsonResponse( { 'cameras': {} } )
