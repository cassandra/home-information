"""
Data Import page + Configure form views.

CONFIGURE on the page row opens the credentials form modal (reuses
``IntegrationAttributeItemEditContext`` with ``capability=IMPORT``).
The form's IMPORT submit validates credentials, fetches upstream
candidates via ``Importer.get_candidate_items()``, computes a
new-vs-skipped split against existing HI entities, and renders the
preview modal. Phase 5 wires CONFIRM IMPORT → run.
"""
import logging
from typing import Any, Dict, Optional

from django.urls import reverse

from hi.apps.attribute.view_mixins import AttributeEditViewMixin
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.entity.enums import EntityDataSource
from hi.apps.entity.models import Entity
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.hi_async_view import HiModalView
from hi.views import page_not_found_response

from hi.integrations.enums import IntegrationCapability
from hi.integrations.integration_attribute_edit_context import (
    IntegrationAttributeItemEditContext,
)
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.integrations.placement_request import PlacementUrlParams
from hi.integrations.view_mixins import IntegrationViewMixin

logger = logging.getLogger(__name__)

_IMPORT_CAPABILITY_FILTER = frozenset({ IntegrationCapability.IMPORT })


class DataImportPageView( ConfigPageView, IntegrationViewMixin ):
    """The Data Import tab. Flat list of IMPORT-capable integrations
    with per-row CONFIGURE / DISCARD affordances."""

    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.DATA_IMPORT

    def get_main_template_name(self) -> str:
        return 'integrations/import/pages/data_import_page.html'

    def get_main_template_context(self, request, *args, **kwargs) -> Dict[str, Any]:
        integration_data_list = self.get_integration_data_list(
            capabilities = _IMPORT_CAPABILITY_FILTER,
        )

        # Pre-query which integrations have existing imported entities
        # so the row template can decide whether to render DISCARD.
        # data_source=INTERNAL is the canonical predicate for imported
        # data (Connect-mode HomeBox is EXTERNAL; HA/ZM/Frigate Connect
        # is INTERNAL but they have no IMPORT capability so don't appear).
        has_imported_set = set(
            Entity.objects.filter(
                integration_id__in = [
                    d.integration_id for d in integration_data_list
                ],
                data_source_str = str(EntityDataSource.INTERNAL),
            ).values_list('integration_id', flat=True).distinct()
        )

        rows = []
        for data in integration_data_list:
            rows.append({
                'integration_data': data,
                'has_imported': data.integration_id in has_imported_set,
                'is_dual_capability': (
                    IntegrationCapability.CONNECT in data.integration_metadata.capabilities
                    and IntegrationCapability.IMPORT in data.integration_metadata.capabilities
                ),
            })

        return {
            'rows': rows,
        }


class ImporterConfigureView( HiModalView, IntegrationViewMixin, AttributeEditViewMixin ):
    """Credentials form for IMPORT. The form's submit (IMPORT) runs
    validate_configuration + validate_access, fetches candidates, and
    renders the preview modal with new/skipped counts. No DB writes
    to entities yet — that happens in Phase 5's confirm step."""

    def get_template_name(self) -> str:
        return 'integrations/import/importer_configure.html'

    def get(self, request, *args, **kwargs):
        integration_manager = IntegrationManager()
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        integration_manager.ensure_all_attributes_exist(
            integration_metadata = integration_data.integration_metadata,
            integration = integration_data.integration,
        )
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability = IntegrationCapability.IMPORT,
            update_button_label = 'IMPORT',
            suppress_history = True,
            show_secrets = True,
        )
        template_context = self.create_initial_template_context(
            attr_item_context = attr_item_context,
        )
        return self.modal_response(request, template_context)

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        attr_item_context = IntegrationAttributeItemEditContext(
            integration_data = integration_data,
            capability = IntegrationCapability.IMPORT,
            update_button_label = 'IMPORT',
            suppress_history = True,
            show_secrets = True,
        )
        response = self.post_attribute_form(
            request = request,
            attr_item_context = attr_item_context,
        )
        # Errors re-render the form with messages.
        if response.status_code > 299:
            return response

        # Synchronously refresh the integration's singleton manager so
        # the freshly-saved credentials are visible before the importer
        # reads them. The post_save signal eventually delivers this via
        # DelayedSignalProcessor, but the 0.1s delay races the immediate
        # importer call.
        try:
            integration_data.integration_gateway.notify_settings_changed()
        except Exception as e:
            logger.warning(
                f'Synchronous notify_settings_changed failed for '
                f'{integration_data.integration_id}: {e}'
            )

        # Validation passed. Fetch candidates and compute counts.
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
                template_name = 'integrations/import/import_preview.html',
            )

        candidates = importer.get_candidate_items()
        existing_names = set(
            Entity.objects.filter(
                integration_id = integration_data.integration_id,
            ).values_list('integration_name', flat=True)
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
                'run_url': run_url,
            },
            template_name = 'integrations/import/import_preview.html',
        )

    def validate_attributes_extra(
            self, attr_item_context, regular_attributes_formset, request,
    ) -> Optional[Any]:
        """AttributeEditViewMixin hook: schema + access validation."""
        self.validate_attributes_extra_helper(
            attr_item_context,
            regular_attributes_formset,
            error_title = 'Cannot configure import.',
        )
        return


class ImporterRunView( HiModalView, IntegrationViewMixin ):
    """CONFIRM IMPORT handler. Runs the importer, invalidates the
    metadata + sensor-response caches, renders the result modal with
    a placement CTA when new entities were created."""

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
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
            template_name = 'integrations/import/import_result.html',
        )


class ImporterDiscardView( HiModalView, IntegrationViewMixin ):
    """DISCARD handler. GET renders the confirmation modal with the
    count of imported entities; POST runs discard_imported_data and
    redirects back to the Data Import page. Single-action confirm —
    imported items ARE the user data, so the Connect-side SAFE/ALL
    split doesn't apply."""

    def get_template_name(self) -> str:
        return 'integrations/import/import_discard_confirm.html'

    def get(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
        imported_count = Entity.objects.filter(
            integration_id = integration_data.integration_id,
            data_source_str = str(EntityDataSource.INTERNAL),
        ).count()
        return self.modal_response(
            request,
            context = {
                'integration_data': integration_data,
                'imported_count': imported_count,
            },
        )

    def post(self, request, *args, **kwargs):
        integration_id = kwargs.get('integration_id')
        integration_data = self.get_integration_data(
            integration_id = integration_id,
        )
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
