"""View tests for the Data Import page and the Configure form."""
import logging
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.enums import IntegrationAttributeType, IntegrationCapability
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.importer.transient_models import (
    CandidateItem,
    IntegrationDiscardResult,
    IntegrationImportResult,
)
from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import Integration
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)

logging.disable(logging.CRITICAL)


class _ImportTestAttributeType(IntegrationAttributeType):
    TEST_ATTR = (
        'Test Attribute', '',
        AttributeValueType.TEXT, {}, True, True, 'default',
    )


class _ImportCapableGateway(IntegrationGateway):
    """Gateway that supports IMPORT (with optional CONNECT too)."""

    def __init__(self, integration_id='hb', capabilities=None, candidates=None):
        self.integration_id = integration_id
        self._capabilities = (
            capabilities if capabilities is not None
            else frozenset({ IntegrationCapability.IMPORT })
        )
        self._candidates = candidates or []

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Import Test',
            attribute_type=_ImportTestAttributeType,
            allow_entity_deletion=True,
            capabilities=self._capabilities,
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def validate_access(self, integration_attributes, timeout_secs):
        return ConnectionTestResult.success()

    def get_importer(self) -> IntegrationImporter:
        importer = IntegrationImporter()
        importer.get_candidate_items = lambda: list(self._candidates)

        # Real DISCARD semantics: delete imported (provenance-carrying)
        # rows for this integration_id. Mirrors HomeBoxImporter for
        # test purposes.
        def _stub_discard(integration_id):
            qs = Entity.objects.imported_for(integration_id=integration_id)
            count = qs.count()
            qs.delete()
            return IntegrationDiscardResult(count=count)
        importer.discard_imported_data = _stub_discard
        return importer


class _ConnectOnlyGateway(IntegrationGateway):
    """Gateway that does NOT declare IMPORT (Connect-only). Should not
    appear on the Data Import page."""

    def __init__(self, integration_id='hass'):
        self.integration_id = integration_id

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Connect Only Test',
            attribute_type=_ImportTestAttributeType,
            allow_entity_deletion=True,
            capabilities=frozenset({ IntegrationCapability.CONNECT }),
        )


def _populate_manager(integration_ids_and_gateways):
    manager = IntegrationManager()
    manager._integration_data_map = {}
    for integration_id, gateway in integration_ids_and_gateways:
        integration, _ = Integration.objects.get_or_create(
            integration_id=integration_id,
            defaults={'is_enabled': False},
        )
        manager._integration_data_map[integration_id] = IntegrationData(
            integration_gateway=gateway,
            integration=integration,
        )


class DataImportPageViewTests(TestCase):

    def setUp(self):
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None

    def test_lists_only_import_capable_integrations(self):
        _populate_manager([
            ('hb', _ImportCapableGateway('hb')),
            ('hass', _ConnectOnlyGateway('hass')),
        ])
        response = self.client.get(reverse('integrations_import_home'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Import Test', body)
        self.assertNotIn('Connect Only Test', body)

    def test_discard_renders_only_when_imported_entities_exist(self):
        _populate_manager([
            ('hb', _ImportCapableGateway('hb')),
        ])
        response_no_imports = self.client.get(reverse('integrations_import_home'))
        self.assertNotIn(
            reverse('integrations_import_discard', kwargs={'integration_id': 'hb'}),
            response_no_imports.content.decode(),
        )

        Entity.objects.create(
            previous_integration_id='hb',
            previous_integration_name='item-1',
            name='Imported',
            entity_type_str=str(EntityType.OTHER),
        )
        response_with_imports = self.client.get(reverse('integrations_import_home'))
        self.assertIn(
            reverse('integrations_import_discard', kwargs={'integration_id': 'hb'}),
            response_with_imports.content.decode(),
        )

    def test_dual_capability_row_shows_integration_note(self):
        _populate_manager([
            ('hb', _ImportCapableGateway(
                'hb',
                capabilities=frozenset({
                    IntegrationCapability.CONNECT,
                    IntegrationCapability.IMPORT,
                }),
            )),
        ])
        response = self.client.get(reverse('integrations_import_home'))
        self.assertIn('Also available as a Connector', response.content.decode())


class ImporterConfigureViewTests(TestCase):

    INTEGRATION_ID = 'hb'

    def setUp(self):
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None

    def _url(self):
        return reverse(
            'integrations_import_configure',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_get_renders_form_with_import_button(self):
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(self.INTEGRATION_ID)),
        ])
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Import Test', body)
        # The form's submit button label is IMPORT.
        self.assertIn('>\n          IMPORT\n        </button>', body)

    def test_post_run_renders_result_modal_with_placement_cta(self):
        # Stub importer that returns a result with a placement_input
        # pointing at a freshly-created entity.
        entity = Entity.objects.create(
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='item-fresh',
            name='Fresh Item',
            entity_type_str=str(EntityType.OTHER),
        )
        gateway = _ImportCapableGateway(self.INTEGRATION_ID)
        stub_importer = IntegrationImporter()
        stub_importer.run_import = lambda: IntegrationImportResult(
            title='Import Result',
            items_imported_count=1,
            imported_list=['Fresh Item'],
            placement_input=EntityPlacementInput(
                ungrouped_items=[
                    EntityPlacementItem(
                        key=f'entity:{entity.id}',
                        label=entity.name,
                        entity=entity,
                    ),
                ],
            ),
        )
        gateway.get_importer = lambda: stub_importer
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        response = self.client.post(reverse(
            'integrations_import_run',
            kwargs={'integration_id': self.INTEGRATION_ID},
        ))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Import complete', body)
        self.assertIn('Fresh Item', body)
        # Placement CTA renders the placement URL.
        self.assertIn('Place new items', body)
        self.assertIn('placement', body)

    _DUAL_CAPS = frozenset({
        IntegrationCapability.CONNECT,
        IntegrationCapability.IMPORT,
    })

    def test_get_import_blocked_by_existing_connect_data(self):
        # Dual-capability integration with existing Connect-mode
        # (EXTERNAL) entities and no Import-mode entities: opening
        # Import-side CONFIGURE returns the block modal pointing at
        # the Integrations tab.
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(
                self.INTEGRATION_ID,
                capabilities=self._DUAL_CAPS,
            )),
        ])
        Entity.objects.create(
            integration_id=self.INTEGRATION_ID,
            integration_name='connected-1',
            name='Connected',
            entity_type_str=str(EntityType.OTHER),
        )
        response = self.client.get(self._url())
        body = response.content.decode()
        self.assertIn('Cannot configure', body)
        self.assertIn('GO TO CONNECTORS', body)
        self.assertIn(reverse('integrations_connect_home'), body)

    def test_get_import_not_blocked_for_single_capability_integration(self):
        # Hypothetical Import-only integration (no CONNECT): block
        # never fires even with EXTERNAL entities laying around.
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(
                self.INTEGRATION_ID,
                capabilities=frozenset({ IntegrationCapability.IMPORT }),
            )),
        ])
        Entity.objects.create(
            integration_id=self.INTEGRATION_ID,
            integration_name='stale-external',
            name='Stale',
            entity_type_str=str(EntityType.OTHER),
        )
        response = self.client.get(self._url())
        body = response.content.decode()
        self.assertNotIn('Cannot configure', body)

    def _discard_url(self):
        return reverse(
            'integrations_import_discard',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_get_discard_renders_confirm_with_count(self):
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(self.INTEGRATION_ID)),
        ])
        for i in range(3):
            Entity.objects.create(
                previous_integration_id=self.INTEGRATION_ID,
                previous_integration_name=f'item-{i}',
                name=f'Item {i}',
                entity_type_str=str(EntityType.OTHER),
            )

        response = self.client.get(self._discard_url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Discard imported', body)
        # Count appears in the body.
        self.assertIn('3', body)
        self.assertIn('DISCARD', body)

    def test_get_discard_with_zero_imported_hides_action(self):
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(self.INTEGRATION_ID)),
        ])
        response = self.client.get(self._discard_url())
        body = response.content.decode()
        self.assertIn('No imported items to discard', body)

    def test_post_discard_deletes_imported_and_leaves_connect_alone(self):
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(self.INTEGRATION_ID)),
        ])
        Entity.objects.create(
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='imported-1',
            name='Imported',
            entity_type_str=str(EntityType.OTHER),
        )
        Entity.objects.create(
            integration_id=self.INTEGRATION_ID,
            integration_name='connected-1',
            name='Connected',
            entity_type_str=str(EntityType.OTHER),
        )

        response = self.client.post(self._discard_url(), {})

        self.assertTrue(200 <= response.status_code < 400)
        self.assertFalse(
            Entity.objects.filter(previous_integration_name='imported-1').exists()
        )
        self.assertTrue(
            Entity.objects.filter(integration_name='connected-1').exists()
        )

    def test_post_run_renders_nothing_imported_when_all_skipped(self):
        gateway = _ImportCapableGateway(self.INTEGRATION_ID)
        stub_importer = IntegrationImporter()
        stub_importer.run_import = lambda: IntegrationImportResult(
            title='Import Result',
            items_imported_count=0,
            items_skipped_count=3,
        )
        gateway.get_importer = lambda: stub_importer
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        response = self.client.post(reverse(
            'integrations_import_run',
            kwargs={'integration_id': self.INTEGRATION_ID},
        ))
        body = response.content.decode()
        self.assertIn('Nothing imported', body)
        self.assertNotIn('Place ', body)

    def test_post_with_valid_attrs_renders_preview_with_counts(self):
        candidates = [
            CandidateItem(name='Item One', integration_name='item-1'),
            CandidateItem(name='Item Two', integration_name='item-2'),
        ]
        _populate_manager([
            (self.INTEGRATION_ID, _ImportCapableGateway(
                self.INTEGRATION_ID,
                candidates=candidates,
            )),
        ])
        # Pre-existing entity for item-2 so the preview counts skip=1, new=1.
        Entity.objects.create(
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='item-2',
            name='Already',
            entity_type_str=str(EntityType.OTHER),
        )

        from hi.integrations.importer.views import ImporterConfigureView
        from django.http import HttpResponse
        with patch.object(
                ImporterConfigureView, 'post_attribute_form',
                return_value=HttpResponse(status=200),
        ):
            response = self.client.post(self._url(), {})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Would import', body)
        self.assertIn('1', body)  # 1 new
        self.assertIn('CONFIRM IMPORT', body)
