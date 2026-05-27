"""
Data Import page + Configure form views.

CONFIGURE on the page row opens the credentials form modal (reuses
``IntegrationAttributeItemEditContext`` with ``capability=IMPORT``).
The form's IMPORT submit validates credentials, fetches upstream
candidates via ``IntegrationImporter.get_candidate_items()``, computes a
new-vs-skipped split against existing HI entities, and renders the
preview modal. Phase 5 wires CONFIRM IMPORT → run.
"""
import logging
from typing import Any, Dict

from django.urls import reverse

from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.models import Entity
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.integrations.placement_request import PlacementUrlParams
from hi.integrations.view_mixins import IntegrationViewMixin
from hi.integrations.views import CapabilityConfigureView

logger = logging.getLogger(__name__)

_IMPORT_CAPABILITY_FILTER = frozenset({ IntegrationCapability.IMPORT })


class DataImportPageView( ConfigPageView, IntegrationViewMixin ):
    """The Data Import tab. Flat list of IMPORT-capable integrations
    with per-row CONFIGURE / DISCARD affordances."""

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.INTEGRATIONS_IMPORT

    def get_main_template_name(self) -> str:
        return 'integrations/importer/pages/data_import_page.html'

    def get_main_template_context(self, request, *args, **kwargs) -> Dict[str, Any]:
        integration_data_list = self.get_integration_data_list(
            capabilities = _IMPORT_CAPABILITY_FILTER,
        )

        rows = []
        for data in integration_data_list:
            rows.append({
                'integration_data': data,
                'has_imported': Entity.objects.imported_for(
                    integration_id = data.integration_id,
                ).exists(),
                'is_dual_capability': (
                    IntegrationCapability.CONNECT in data.integration_metadata.capabilities
                    and IntegrationCapability.IMPORT in data.integration_metadata.capabilities
                ),
            })

        return {
            'rows': rows,
        }


class ImporterConfigureView( CapabilityConfigureView ):
    """Credentials form for IMPORT. The form's submit (IMPORT) runs
    validate_configuration + validate_access, fetches candidates, and
    renders the preview modal with new/skipped counts. No DB writes
    to entities yet — that happens in the confirm step."""

    capability    = IntegrationCapability.IMPORT
    button_label  = 'IMPORT'
    template_name = 'integrations/importer/modals/importer_configure.html'
    error_title   = 'Cannot configure import.'

    def get_capability_gateway( self, integration_data ):
        return integration_data.integration_gateway.get_importer()

    def handle_post_success(self, request, integration_data):
        # Synchronously refresh the integration's singleton manager so
        # the freshly-saved credentials are visible before the importer
        # reads them. The post_save signal eventually delivers this via
        # DelayedSignalProcessor, but the 0.1s delay races the
        # immediate get_candidate_items() call.
        try:
            integration_data.integration_gateway.notify_settings_changed()
        except Exception as e:
            logger.warning(
                f'Synchronous notify_settings_changed failed for '
                f'{integration_data.integration_id}: {e}'
            )

        importer = integration_data.integration_gateway.get_importer()
        if importer is None:
            return self.modal_response(
                request,
                context = {
                    'integration_data': integration_data,
                    'error_message': (
                        f'{integration_data.label} does not support import.'
                    ),
                },
                template_name = 'integrations/importer/modals/import_preview.html',
            )

        candidates = importer.get_candidate_items()
        existing_names = set(
            Entity.objects.imported_for(
                integration_id = integration_data.integration_id,
            ).values_list( 'previous_integration_name', flat = True )
        )
        new_count = sum(
            1 for c in candidates if c.integration_name not in existing_names
        )
        skipped_count = len(candidates) - new_count

        run_url = reverse(
            'integrations_import_run',
            kwargs = { 'integration_id': integration_data.integration_id },
        )
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'new_count': new_count,
                'skipped_count': skipped_count,
                'existing_imported_count': len(existing_names),
                'run_url': run_url,
            },
            template_name = 'integrations/importer/modals/import_preview.html',
        )


class DataImportInfoView( HiModalView ):
    """Static info modal explaining Data Import vs. Integration."""

    def get_template_name(self) -> str:
        return 'integrations/importer/modals/data_import_info.html'


class ImporterRunView( HiModalView, IntegrationViewMixin ):
    """CONFIRM IMPORT handler. Runs the importer, invalidates the
    metadata + sensor-response caches, renders the result modal with
    a placement CTA when new entities were created."""

    def post(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        importer = integration_data.integration_gateway.get_importer()
        if importer is None:
            return page_not_found_response(request)

        try:
            result = importer.run_import()
        finally:
            # Mirror the post-sync invalidations so any cached
            # metadata or sensor-response state pinned by polls that
            # raced the import gets dropped.
            IntegrationMetadataCache().invalidate()
            SensorResponseManager().invalidate_local_sensor_cache()

        if result.created_entities:
            result.placement_input = integration_data.integration_gateway.group_entities_for_placement(
                entities = result.created_entities,
            )

        new_entity_ids = (
            result.placement_input.all_entity_ids()
            if result.placement_input is not None else []
        )
        placement_url = PlacementUrlParams(
            is_initial_connect = True,
            entity_ids = new_entity_ids,
        ).append_to_url( reverse(
            'integrations_placement',
            kwargs = { 'integration_id': integration_data.integration_id },
        ) )

        return self.modal_response(
            request,
            context = {
                'result': result,
                'integration_data': integration_data,
                'placement_url': placement_url,
            },
            template_name = 'integrations/importer/modals/import_result.html',
        )


class ImporterDiscardView( HiModalView, IntegrationViewMixin ):
    """DISCARD handler. GET renders the confirmation modal with the
    count of imported entities; POST runs discard_imported_data and
    redirects back to the Data Import page. Single-action confirm —
    imported items ARE the user data, so the Connect-side SAFE/ALL
    split doesn't apply."""

    def get_template_name(self) -> str:
        return 'integrations/importer/modals/import_discard_confirm.html'

    def get(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        imported_count = Entity.objects.imported_for(
            integration_id = integration_data.integration_id,
        ).count()
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'imported_count': imported_count,
            },
        )

    def post(self, request, *args, **kwargs):
        integration_data = self.get_integration_data( request, *args, **kwargs )
        importer = integration_data.integration_gateway.get_importer()
        if importer is None:
            return page_not_found_response(request)

        try:
            importer.discard_imported_data(
                integration_id = integration_data.integration_id,
            )
        finally:
            # Mirror the Connect-side Disable cleanup: any cached
            # metadata / sensor-response state for the just-deleted
            # entities must drop too.
            IntegrationMetadataCache().invalidate()
            SensorResponseManager().invalidate_local_sensor_cache()

        redirect_url = reverse('integrations_import_home')
        return self.redirect_response(request, redirect_url)
