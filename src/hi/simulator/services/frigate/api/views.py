"""Frigate-shape HTTP API views (simulator-side).

Each view returns the JSON shape a real Frigate instance would
respond with, so HI's ``FrigateClient`` can talk to the simulator
without any client-side branching.
"""
import logging
from datetime import datetime, timezone

from django.http import Http404, JsonResponse
from django.views.generic import View

from hi.simulator.services.frigate.event_manager import FrigateSimEventManager
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


class EventsListView( View ):
    """``GET /api/events`` — Frigate's events listing.

    v1 supports the ``after`` query parameter (epoch seconds), which
    is what the HI polling cursor will use. Other Frigate filters
    (``before`` / ``cameras`` / ``labels`` / ``zones``) are accepted
    and silently ignored — they're not on the HI integration's read
    path yet. Response is a top-level JSON array, most-recent
    start_time first (Frigate's convention)."""

    def get(self, request, *args, **kwargs):
        try:
            after_param = request.GET.get( 'after' )
            event_manager = FrigateSimEventManager()
            if after_param is not None:
                try:
                    after_epoch = float( after_param )
                except ValueError:
                    return JsonResponse(
                        { 'error': f'Invalid after parameter: {after_param!r}' },
                        status = 400,
                    )
                cutoff = datetime.fromtimestamp( after_epoch, tz = timezone.utc )
                events = event_manager.get_events_after( start_datetime = cutoff )
            else:
                events = event_manager.all_events()

            # Frigate orders events newest-first by start_time.
            events.sort( key = lambda e : e.start_datetime, reverse = True )
            return JsonResponse(
                [ e.to_api_dict() for e in events ],
                safe = False,
            )
        except Exception:
            logger.exception( 'Problem processing Frigate /api/events request.' )
            return JsonResponse( [], safe = False )


class EventDetailView( View ):
    """``GET /api/events/<id>`` — single Frigate event detail.

    Used by HI's integration to fetch event-specific data (snapshot
    URL, clip URL, full metadata). 404s for unknown ids so the HI
    client can distinguish "event doesn't exist" from "Frigate is
    broken"."""

    def get(self, request, event_id : str, *args, **kwargs):
        event = FrigateSimEventManager().find_event_by_id( event_id = event_id )
        if event is None:
            raise Http404( f'Unknown Frigate event id: {event_id!r}' )
        return JsonResponse( event.to_api_dict() )
