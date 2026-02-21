from typing import Dict, List

from django.db import transaction

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.transient_models import IntegrationKey

from .hb_metadata import HbMetaData


class HbConverter:

    @classmethod
    def create_models_for_hb_item( cls, hb_item ) -> Entity:
        with transaction.atomic():
            entity_name = cls.hb_item_to_entity_name( hb_item = hb_item )
            entity_payload = cls.hb_item_to_integration_payload( hb_item = hb_item )

            entity = Entity(
                name = entity_name,
                entity_type_str = str( cls.hb_item_to_entity_type( hb_item = hb_item ) ),
                can_user_delete = HbMetaData.allow_entity_deletion,
                integration_payload = entity_payload,
            )
            entity.integration_key = cls.hb_item_to_integration_key( hb_item = hb_item )
            entity.save()

        return entity

    @classmethod
    def update_models_for_hb_item( cls, entity : Entity, hb_item ) -> List[str]:
        messages = list()

        with transaction.atomic():
            entity_name = cls.hb_item_to_entity_name( hb_item = hb_item )
            if entity.name != entity_name:
                messages.append( f'Name changed for {entity}. Setting to "{entity_name}"' )
                entity.name = entity_name

            entity_type = cls.hb_item_to_entity_type( hb_item = hb_item )
            if entity.entity_type != entity_type:
                messages.append( f'Type changed for {entity}. Setting to "{entity_type}"' )
                entity.entity_type = entity_type

            new_payload = cls.hb_item_to_integration_payload( hb_item = hb_item )
            if entity.integration_payload != new_payload:
                messages.append( 'Integration payload updated' )
                entity.integration_payload = new_payload

            if messages:
                entity.save()

        return messages

    @classmethod
    def hb_item_to_integration_key( cls, hb_item ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = HbMetaData.integration_id,
            integration_name = str( hb_item.id ),
        )

    @classmethod
    def hb_item_to_entity_name( cls, hb_item ) -> str:
        item_name = getattr( hb_item, 'name', '' )
        if item_name:
            return item_name
        return f'HomeBox Item {hb_item.id}'

    @classmethod
    def hb_item_to_entity_type( cls, hb_item ) -> EntityType:
        return EntityType.OTHER

    @classmethod
    def hb_item_to_integration_payload( cls, hb_item ) -> Dict:
        location = getattr( hb_item, 'location', None ) or {}
        labels = getattr( hb_item, 'labels', None ) or []

        if not isinstance( location, dict ):
            location = {}

        label_name_list = list()
        for label in labels:
            if isinstance( label, dict ):
                label_name = label.get( 'name' )
            else:
                label_name = getattr( label, 'name', None )
            if label_name:
                label_name_list.append( label_name )
            continue

        return {
            'description': getattr( hb_item, 'description', '' ),
            'quantity': getattr( hb_item, 'quantity', None ),
            'location_id': location.get( 'id' ),
            'location_name': location.get( 'name' ),
            'label_names': sorted( label_name_list ),
        }
