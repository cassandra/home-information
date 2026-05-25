from typing import List, Optional
import logging

from django.db import transaction

from hi.apps.entity.models import Entity
from hi.integrations.enums import IntegrationCapability

from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_models import HbItem

logger = logging.getLogger(__name__)


class HbEntityFactory:
    """Builds and updates HI Entity rows from HomeBox upstream items.

    Shared by HomeBox's CONNECT-mode synchronizer and IMPORT-mode
    importer. The ``capability`` parameter selects the entity-mode
    flags: CONNECT produces read-only mirror entities owned by
    HomeBox; IMPORT produces HI-owned editable entities."""

    @classmethod
    def create_models_for_hb_item( cls,
                                   hb_item    : HbItem,
                                   capability : IntegrationCapability,
                                   entity     : Optional[Entity] = None ) -> Entity:
        """
        Create or repopulate the integration-owned components for an
        HbItem. When ``entity`` is None (the standard create path), a
        fresh Entity is created from the upstream payload. When
        ``entity`` is provided (the auto-reconnect path from Issue
        #281), the integration-owned fields on that entity are
        repopulated; the entity's ``name`` is deliberately preserved
        because the user may have edited it before/after the
        intervening disconnect.
        """
        with transaction.atomic():
            entity_integration_key = HbConverter.hb_item_to_integration_key( hb_item = hb_item )
            entity_payload = HbConverter.hb_item_to_entity_payload( hb_item = hb_item )

            if entity is None:
                entity = Entity(
                    name = HbConverter.hb_item_to_entity_name( hb_item = hb_item ),
                    entity_type_str = str( HbConverter.hb_item_to_entity_type( hb_item = hb_item ) ),
                )

            entity.integration_payload = entity_payload
            if capability == IntegrationCapability.IMPORT:
                # Import-mode: HI owns the entity from day one but
                # carries upstream provenance for re-import skip-
                # detection and for the auto-reconnect path if the
                # user later enables CONNECT. The provenance is
                # recorded on previous_integration_*; integration_id
                # stays NULL because no live integration owns this
                # row.
                entity.integration_key = None
                entity.previous_integration_key = entity_integration_key
                entity.can_user_delete = True
                entity.allow_internal_attributes = True
            else:
                # CONNECT-mode (and any other capability): HomeBox
                # remains the source of truth. Setting integration_key
                # also clears previous_integration_* via the setter —
                # safe whether this is a fresh-create or a reconnect
                # of a previously-detached/imported row.
                entity.integration_key = entity_integration_key
                entity.can_user_delete = HbMetaData.allow_entity_deletion
                entity.allow_internal_attributes = HbMetaData.allow_internal_attributes
            entity.save()

        return entity

    @classmethod
    def update_models_for_hb_item( cls, entity : Entity, hb_item ) -> List[str]:
        messages = list()

        with transaction.atomic():
            entity_name = HbConverter.hb_item_to_entity_name( hb_item = hb_item )
            if entity.name != entity_name:
                messages.append( f'Name changed for {entity}. Setting to "{entity_name}"' )
                entity.name = entity_name

            desired_entity_type = HbConverter.hb_item_to_entity_type( hb_item = hb_item )
            if entity.entity_type != desired_entity_type:
                messages.append( f'Entity type changed for {entity}. Setting to "{desired_entity_type}"' )
                entity.entity_type = desired_entity_type

            if entity.allow_internal_attributes != HbMetaData.allow_internal_attributes:
                messages.append( f'allow_internal_attributes changed for {entity}.' )
                entity.allow_internal_attributes = HbMetaData.allow_internal_attributes

            new_payload = HbConverter.hb_item_to_entity_payload( hb_item = hb_item )
            if entity.integration_payload != new_payload:
                entity.integration_payload = new_payload
                messages.append( f'Integration payload updated for {entity}.' )

            if messages:
                entity.save()

        return messages
