"""Framework-level IntegrationGateway tests — exercises the
defaults that integrations either inherit or override.
"""
import logging

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.integration_gateway import IntegrationGateway

logging.disable(logging.CRITICAL)


class TestIntegrationGatewayPlacementItemKey(TestCase):
    """Verify the three precedence branches of the unified
    _placement_item_key helper:

      1. live integration_key  -> "<id>:<name>"
      2. previous_integration_key (detached/imported) -> "<id>:<name>"
      3. neither populated (native) -> "entity:<id>"

    Precedence is enforced by integration_key.setter clearing the
    previous-pair on attach, so only one of the keys is populated
    in any real lifecycle state."""

    def setUp(self):
        self.gateway = IntegrationGateway()

    def test_uses_integration_key_when_attached(self):
        entity = Entity.objects.create(
            name='Live',
            entity_type_str=str(EntityType.LIGHT),
            integration_id='hass',
            integration_name='light.kitchen',
        )
        self.assertEqual(
            self.gateway._placement_item_key(entity=entity),
            'hass:light.kitchen',
        )

    def test_uses_previous_integration_key_when_detached(self):
        entity = Entity.objects.create(
            name='Detached',
            entity_type_str=str(EntityType.LIGHT),
            previous_integration_id='hb',
            previous_integration_name='item.42',
        )
        self.assertEqual(
            self.gateway._placement_item_key(entity=entity),
            'hb:item.42',
        )

    def test_falls_back_to_entity_id_when_native(self):
        entity = Entity.objects.create(
            name='Native',
            entity_type_str=str(EntityType.OTHER),
        )
        self.assertEqual(
            self.gateway._placement_item_key(entity=entity),
            f'entity:{entity.id}',
        )
