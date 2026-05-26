"""HomeBox concrete IntegrationImporter.

Implements the IntegrationImporter protocol for HomeBox. The Connect-mode
connector lives at ``services/homebox/connector/homebox_connector.py``;
this is the parallel for the IMPORT capability.

Import is add-only: items not already present in HI (by
integration_name match) get created as user-owned (INTERNAL)
entities; existing matches are skipped and surfaced as the
preview's skip count.
"""
import logging
from typing import List

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.entity.models import Entity

from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.enums import IntegrationCapability
from hi.integrations.entity_operations import EntityIntegrationOperations
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.importer.transient_models import (
    CandidateItem,
    IntegrationDiscardResult,
    IntegrationImportResult,
)
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationMetaData, IntegrationValidationResult

from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_filter_footer import HB_FILTER_FOOTER_MESSAGE
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_mixins import HomeBoxMixin
from hi.services.homebox.hb_models import HbItem
from hi.services.homebox.hb_entity_factory import HbEntityFactory

from .hb_importer import populate_attributes_for_imported_entity

logger = logging.getLogger(__name__)


class HomeBoxImporter( IntegrationImporter, HomeBoxMixin ):

    def get_metadata(self) -> IntegrationMetaData:
        return HbMetaData

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute],
    ) -> IntegrationValidationResult:
        return self.hb_manager().validate_configuration(
            integration_attributes = integration_attributes,
        )

    def get_candidate_items(self) -> List[CandidateItem]:
        """Lightweight upstream pull for the preview step. Returns the
        full upstream item list as ``CandidateItem``s; the framework
        decides which are new vs. already-imported by comparing
        ``integration_name`` against existing HI entities. The
        include/exclude filter is applied here so the preview count
        matches what ``run_import`` will actually pull."""
        hb_manager = self.hb_manager()
        if not hb_manager.hb_client:
            return []
        summary_list = hb_manager.fetch_hb_items_summary_from_api()
        include_tokens = HbConverter.parse_filter_list( hb_manager.include_filter )
        exclude_tokens = HbConverter.parse_filter_list( hb_manager.exclude_filter )
        filter_active = bool( include_tokens or exclude_tokens )
        candidates: List[CandidateItem] = []
        for summary in summary_list:
            item_id = summary.get( 'id' )
            if item_id is None:
                continue
            # ``archived: true`` upstream items are skipped — they
            # mirror the same filter as the Connect-mode sync check
            # so imports don't pull HomeBox's tombstones.
            if summary.get( 'archived' ) is True:
                continue
            if filter_active and not HbConverter.is_item_allowed(
                    hb_item = HbItem( api_dict = summary ),
                    include_tokens = include_tokens,
                    exclude_tokens = exclude_tokens ):
                continue
            candidates.append( CandidateItem(
                name = summary.get( 'name' ) or f'HomeBox Item {item_id}',
                integration_name = str( item_id ),
            ) )
        return candidates

    def run_import(self) -> IntegrationImportResult:
        """Execute the import. Per-entity transaction so one item's
        failure does not abort the batch. Shares the
        ``integrations_sync`` exclusion lock with Connect-side sync
        so Import and Connect serialize against each other."""
        result = IntegrationImportResult( title = 'Import Result' )
        with ExclusionLockContext( name = IntegrationConnector.SYNCHRONIZATION_LOCK_NAME ):
            self._run_import_locked( result = result )
        return result

    def _run_import_locked(self, result: IntegrationImportResult) -> None:
        hb_manager = self.hb_manager()
        if not hb_manager.hb_client:
            reason = (
                hb_manager.health_status.last_message
                or 'HomeBox integration is disabled or not configured.'
            )
            result.error_list.append( f'Cannot import from HomeBox: {reason}' )
            return

        try:
            item_list = hb_manager.fetch_hb_items_from_api()
        except Exception as e:
            logger.exception( 'HomeBox import failed during fetch.' )
            result.error_list.append( f'Cannot import from HomeBox: {e}' )
            return

        # Skip-detection against already-imported rows.
        existing_integration_names = set(
            Entity.objects.imported_for(
                integration_id = HbMetaData.integration_id,
            ).values_list( 'previous_integration_name', flat = True )
        )

        include_tokens = HbConverter.parse_filter_list( hb_manager.include_filter )
        exclude_tokens = HbConverter.parse_filter_list( hb_manager.exclude_filter )
        filter_active = bool( include_tokens or exclude_tokens )

        created_entities = []
        for hb_item in item_list:
            if hb_item.archived is True:
                continue
            if filter_active and not HbConverter.is_item_allowed(
                    hb_item = hb_item,
                    include_tokens = include_tokens,
                    exclude_tokens = exclude_tokens ):
                result.items_filtered_count += 1
                continue
            integration_name = str( hb_item.id )
            if integration_name in existing_integration_names:
                result.items_skipped_count += 1
                continue
            try:
                with transaction.atomic():
                    entity = HbEntityFactory.create_models_for_hb_item(
                        hb_item = hb_item,
                        capability = IntegrationCapability.IMPORT,
                    )
                    populate_attributes_for_imported_entity(
                        entity = entity,
                        hb_item = hb_item,
                    )
            except Exception as e:
                logger.exception(
                    f'HomeBox import failed for item {integration_name}.'
                )
                result.error_list.append(
                    f'Item {integration_name}: {e}'
                )
                continue
            result.items_imported_count += 1
            result.imported_list.append( entity.name )
            created_entities.append( entity )

        result.created_entities = created_entities

        if result.items_filtered_count > 0:
            result.info_list.append(
                f'Filtered {result.items_filtered_count} item(s) not matching your include/exclude filter.'
            )
            result.footer_message = HB_FILTER_FOOTER_MESSAGE

    def discard_imported_data( self, integration_id: str ) -> IntegrationDiscardResult:
        """Remove all entities previously imported under this
        integration_id. Any coexisting active-Connect entities for
        the same integration are untouched."""
        seed_ids = set(
            Entity.objects.imported_for(
                integration_id = integration_id,
            ).values_list( 'id', flat = True )
        )
        if not seed_ids:
            return IntegrationDiscardResult( count = 0 )
        try:
            EntityIntegrationOperations.remove_entities_with_closure(
                seed_entity_ids = seed_ids,
                integration_name = HbMetaData.label,
                preserve_user_data = False,
                result = None,
            )
        except Exception as e:
            logger.exception( f'HomeBox discard failed for {integration_id}.' )
            return IntegrationDiscardResult(
                count = 0,
                errors = [ str( e ) ],
            )
        return IntegrationDiscardResult( count = len( seed_ids ) )
