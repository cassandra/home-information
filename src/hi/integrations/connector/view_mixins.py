from django.urls import reverse

from hi.apps.entity.models import Entity
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.views import page_not_found_response

from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.integrations.placement_request import PlacementUrlParams


class ConnectorViewMixin:
    """Connect-mode-specific view helpers. Lives in the connector
    sub-package because every method here is meaningful only to the
    Connect capability — sync runs, sync-result modals, and the
    placement CTA off a sync result."""

    def render_sync_result( self,
                            request,
                            integration_data,
                            preserve_user_data : bool = True ):
        """Run the integration's connector and render the
        sync-result modal. Shared by the initial-connect flow
        (ConnectorConfigureView.post after enable) and the update-check
        flow (IntegrationSyncView.post after pre-sync confirm).

        Returns the modal response directly, including the placement
        URL for the 'Place new items' CTA when sync produced new
        entities. Cache invalidations run in a ``finally`` so a
        partial-commit failure during sync also flushes."""
        gateway = integration_data.integration_gateway
        connector = gateway.get_connector()
        if connector is None:
            return page_not_found_response( request )

        is_initial_connect = not Entity.objects.filter(
            integration_id = integration_data.integration_id,
        ).exists()

        try:
            sync_result = connector.sync(
                is_initial_connect = is_initial_connect,
                preserve_user_data = preserve_user_data,
            )
        finally:
            IntegrationMetadataCache().invalidate()
            SensorResponseManager().invalidate_local_sensor_cache()

        if sync_result.created_entities:
            sync_result.placement_input = gateway.group_entities_for_placement(
                entities = sync_result.created_entities,
            )

        new_entity_ids = (
            sync_result.placement_input.all_entity_ids()
            if sync_result.placement_input is not None else []
        )
        placement_url = PlacementUrlParams(
            is_initial_connect = is_initial_connect,
            entity_ids = new_entity_ids,
        ).append_to_url( reverse(
            'integrations_placement',
            kwargs = { 'integration_id': integration_data.integration_id },
        ) )

        return self.modal_response(
            request,
            context = {
                'sync_result': sync_result,
                'integration_data': integration_data,
                'is_initial_connect': is_initial_connect,
                'placement_url': placement_url,
            },
            template_name = 'integrations/connector/modals/sync_result.html',
        )
