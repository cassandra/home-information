"""URL routes for the Frigate simulator.

Mounts the Frigate-shaped HTTP API at ``/services/frigate/api/...``.
The simulator's services-page tab UI is owned by the parent
``hi.simulator.services`` module via the
``service_simulator_manager`` tab dispatch.
"""
from django.urls import include, path


urlpatterns = [
    path( 'api/', include( 'hi.simulator.services.frigate.api.urls' )),
]
