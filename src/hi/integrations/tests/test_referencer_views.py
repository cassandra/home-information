"""View tests for the ATTRIBUTE_REFERENCE picker endpoints
(search + attach). The picker's JS layer hits these endpoints
during operator-driven search-and-attach; behavior here is the
load-bearing contract for the picker UX.
"""
import json
import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.location.models import Location, LocationAttribute
from hi.enums import ItemType, ViewMode
from hi.integrations.enums import IntegrationAttributeType, IntegrationCapability
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import Integration
from hi.integrations.referencer.integration_attribute_referencer import (
    IntegrationAttributeReferencer,
)
from hi.integrations.referencer.transient_models import (
    AttributeReferenceResult,
    WireField,
)
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)
from hi.testing.view_test_base import ViewTestBase


logging.disable(logging.CRITICAL)


# ---- fixtures ----------------------------------------------------


class _RefAttributeType(IntegrationAttributeType):
    TEST_ATTR = (
        'Test Attr', '',
        AttributeValueType.TEXT, {}, True, True, 'default',
    )


class _StubReferencer(IntegrationAttributeReferencer):
    """In-memory referencer the tests inject via the gateway.
    Captures the most recent ``search_references`` args so tests
    can assert dispatch shape."""

    def __init__(self, results=None, raises=None):
        self._results = results or []
        self._raises = raises
        self.last_query = None
        self.last_limit = None

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id='ref',
            label='Ref Test',
            attribute_type=_RefAttributeType,
            allow_entity_deletion=True,
            capabilities=frozenset({IntegrationCapability.ATTRIBUTE_REFERENCE}),
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def search_references(self, query, limit=20):
        self.last_query = query
        self.last_limit = limit
        if self._raises is not None:
            raise self._raises
        return list(self._results)


class _ReferencerCapableGateway(IntegrationGateway):
    """Gateway that advertises ATTRIBUTE_REFERENCE and returns
    the test's stub referencer from ``get_attribute_referencer``."""

    def __init__(self, integration_id='ref', referencer=None,
                 capabilities=None):
        self.integration_id = integration_id
        self._referencer = referencer
        self._capabilities = (
            capabilities if capabilities is not None
            else frozenset({IntegrationCapability.ATTRIBUTE_REFERENCE})
        )

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Ref Test',
            attribute_type=_RefAttributeType,
            allow_entity_deletion=True,
            capabilities=self._capabilities,
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def validate_access(self, integration_attributes, timeout_secs):
        return ConnectionTestResult.success()

    def get_attribute_referencer(self):
        return self._referencer


class _NonReferencerGateway(IntegrationGateway):
    """Gateway that does NOT advertise ATTRIBUTE_REFERENCE."""

    def __init__(self, integration_id='other'):
        self.integration_id = integration_id

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Other',
            attribute_type=_RefAttributeType,
            allow_entity_deletion=True,
            capabilities=frozenset({IntegrationCapability.CONNECT}),
        )


def _populate_manager(pairs):
    manager = IntegrationManager()
    manager._integration_data_map = {}
    for integration_id, gateway in pairs:
        integration, _ = Integration.objects.get_or_create(
            integration_id=integration_id,
            defaults={'is_enabled': False},
        )
        manager._integration_data_map[integration_id] = IntegrationData(
            integration_gateway=gateway,
            integration=integration,
        )


def _result(title='Doc', source_url='https://example.com/doc/1',
            thumbnail_url=None, mime_type=None, snippet=None):
    return AttributeReferenceResult(
        title=title,
        source_url=source_url,
        thumbnail_url=thumbnail_url,
        mime_type=mime_type,
        snippet=snippet,
    )


# ---- gateway default --------------------------------------------


class TestIntegrationGatewayAttributeReferencerDefault(ViewTestBase):
    """The default ``IntegrationGateway`` advertises no
    ATTRIBUTE_REFERENCE referencer — only integrations that
    explicitly opt in do."""

    def test_default_returns_none(self):
        self.assertIsNone(IntegrationGateway().get_attribute_referencer())


# ---- search view ------------------------------------------------


class TestAttributeReferenceSearchView(ViewTestBase):

    INTEGRATION_ID = 'ref'

    def setUp(self):
        super().setUp()
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)

    def _url(self, integration_id=None):
        return reverse(
            'integrations_attribute_reference_search',
            kwargs={'integration_id': integration_id or self.INTEGRATION_ID},
        )

    def test_empty_query_returns_empty_results_without_dispatching(self):
        # An empty / whitespace query short-circuits to ``[]`` and
        # avoids calling the integration. Saves an upstream round-trip
        # while the operator is still typing.
        referencer = _StubReferencer(results=[_result()])
        gateway = _ReferencerCapableGateway(self.INTEGRATION_ID, referencer)
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        response = self.client.post(self._url(), data={WireField.QUERY: '   '})

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body[WireField.RESULTS], [])
        self.assertIsNone(referencer.last_query)

    def test_search_dispatches_to_referencer_and_serializes_results(self):
        referencer = _StubReferencer(results=[
            _result(title='Warranty', source_url='https://p/doc/1',
                    thumbnail_url='https://p/doc/1/thumb',
                    mime_type='application/pdf',
                    snippet='Warranty terms ...'),
            _result(title='Manual', source_url='https://p/doc/2'),
        ])
        gateway = _ReferencerCapableGateway(self.INTEGRATION_ID, referencer)
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        response = self.client.post(
            self._url(),
            data={WireField.QUERY: 'dishwasher', WireField.LIMIT: '50'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(referencer.last_query, 'dishwasher')
        self.assertEqual(referencer.last_limit, 50)
        body = json.loads(response.content)
        rows = body[WireField.RESULTS]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][WireField.SELECTION_TITLE], 'Warranty')
        self.assertEqual(rows[0][WireField.SELECTION_URL], 'https://p/doc/1')
        self.assertEqual(rows[0]['mime_type'], 'application/pdf')

    def test_limit_clamped_to_max(self):
        referencer = _StubReferencer(results=[])
        gateway = _ReferencerCapableGateway(self.INTEGRATION_ID, referencer)
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        self.client.post(
            self._url(),
            data={WireField.QUERY: 'q', WireField.LIMIT: '9999'},
        )

        # Server-side ceiling protects against hostile/buggy clients.
        self.assertEqual(referencer.last_limit, 100)

    def test_invalid_limit_falls_back_to_default(self):
        referencer = _StubReferencer(results=[])
        gateway = _ReferencerCapableGateway(self.INTEGRATION_ID, referencer)
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        self.client.post(
            self._url(),
            data={WireField.QUERY: 'q', WireField.LIMIT: 'not-a-number'},
        )

        self.assertEqual(referencer.last_limit, 20)

    def test_referencer_exception_returns_502(self):
        # Upstream errors propagate as a 502 so the picker JS can
        # render the operator-facing error message without
        # confusing transport-level failures with 4xx user errors.
        referencer = _StubReferencer(raises=RuntimeError('upstream down'))
        gateway = _ReferencerCapableGateway(self.INTEGRATION_ID, referencer)
        _populate_manager([(self.INTEGRATION_ID, gateway)])

        response = self.client.post(self._url(), data={WireField.QUERY: 'q'})

        self.assertEqual(response.status_code, 502)
        body = json.loads(response.content)
        self.assertIn('upstream down', body[WireField.ERROR])

    def test_integration_without_referencer_returns_404(self):
        _populate_manager([(self.INTEGRATION_ID, _NonReferencerGateway(self.INTEGRATION_ID))])

        response = self.client.post(self._url(), data={WireField.QUERY: 'q'})

        self.assertEqual(response.status_code, 404)

    def test_unknown_integration_returns_404(self):
        _populate_manager([])

        response = self.client.post(
            self._url(integration_id='nope'),
            data={WireField.QUERY: 'q'},
        )

        self.assertEqual(response.status_code, 404)


# ---- attach view ------------------------------------------------


class TestAttributeReferenceAttachView(ViewTestBase):

    INTEGRATION_ID = 'ref'

    def setUp(self):
        super().setUp()
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)
        gateway = _ReferencerCapableGateway(
            self.INTEGRATION_ID, _StubReferencer(),
        )
        _populate_manager([(self.INTEGRATION_ID, gateway)])

    def _url(self, integration_id=None):
        return reverse(
            'integrations_attribute_reference_attach',
            kwargs={'integration_id': integration_id or self.INTEGRATION_ID},
        )

    def _entity(self, name='Dishwasher'):
        return Entity.objects.create(
            name=name,
            entity_type_str=str(EntityType.DISHWASHER),
        )

    def _location(self, name='Kitchen'):
        return Location.objects.create(
            name=name,
            svg_fragment_filename='kitchen.svg',
            svg_view_box_str='0 0 100 100',
        )

    def _selections(self, *pairs):
        """Each pair is (title, source_url). Returns the
        JSON-encoded list the view expects."""
        return json.dumps([
            {WireField.SELECTION_TITLE: title, WireField.SELECTION_URL: url}
            for title, url in pairs
        ])

    def test_attach_creates_text_attributes_on_entity(self):
        entity = self._entity()

        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: self._selections(
                ('Warranty', 'https://p/doc/1'),
                ('Manual', 'https://p/doc/2'),
            ),
        })

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body[WireField.CREATED_COUNT], 2)
        self.assertEqual(len(body[WireField.CREATED_IDS]), 2)

        attrs = list(EntityAttribute.objects.filter(entity=entity)
                                            .order_by('id'))
        self.assertEqual(len(attrs), 2)
        self.assertEqual(attrs[0].name, 'Warranty')
        self.assertEqual(attrs[0].value, 'https://p/doc/1')
        self.assertEqual(attrs[0].value_type, AttributeValueType.TEXT)
        self.assertEqual(attrs[0].attribute_type, AttributeType.CUSTOM)
        self.assertEqual(attrs[1].name, 'Manual')

    def test_attach_creates_text_attributes_on_location(self):
        location = self._location()

        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.LOCATION),
            WireField.ITEM_ID: location.id,
            WireField.SELECTIONS: self._selections(
                ('Floor Plan', 'https://p/doc/floor-plan'),
            ),
        })

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body[WireField.CREATED_COUNT], 1)

        attrs = list(LocationAttribute.objects.filter(location=location))
        self.assertEqual(len(attrs), 1)
        self.assertEqual(attrs[0].name, 'Floor Plan')
        self.assertEqual(attrs[0].value, 'https://p/doc/floor-plan')

    def test_empty_selections_creates_nothing(self):
        entity = self._entity()

        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: json.dumps([]),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EntityAttribute.objects.filter(entity=entity).count(), 0)

    def test_unsupported_item_type_returns_400(self):
        # COLLECTION isn't an attribute-owning model per #232 design.
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.COLLECTION),
            WireField.ITEM_ID: 1,
            WireField.SELECTIONS: self._selections(('A', 'https://p/1')),
        })

        self.assertEqual(response.status_code, 400)

    def test_unknown_item_type_returns_400(self):
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: 'banana',
            WireField.ITEM_ID: 1,
            WireField.SELECTIONS: self._selections(('A', 'https://p/1')),
        })

        self.assertEqual(response.status_code, 400)

    def test_invalid_item_id_returns_400(self):
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: 'not-an-int',
            WireField.SELECTIONS: self._selections(('A', 'https://p/1')),
        })

        self.assertEqual(response.status_code, 400)

    def test_missing_owner_returns_404(self):
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: 99999,
            WireField.SELECTIONS: self._selections(('A', 'https://p/1')),
        })

        self.assertEqual(response.status_code, 404)

    def test_malformed_selections_json_returns_400(self):
        entity = self._entity()
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: 'not-json',
        })

        self.assertEqual(response.status_code, 400)

    def test_selection_with_missing_title_returns_400(self):
        # Sanity-check that the per-row validation rejects malformed
        # rows so the operator-facing error is precise.
        entity = self._entity()
        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: json.dumps([
                {WireField.SELECTION_TITLE: '', WireField.SELECTION_URL: 'https://p/1'},
            ]),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(EntityAttribute.objects.filter(entity=entity).count(), 0)

    def test_integration_without_referencer_returns_404(self):
        _populate_manager([(self.INTEGRATION_ID, _NonReferencerGateway(self.INTEGRATION_ID))])
        entity = self._entity()

        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: self._selections(('A', 'https://p/1')),
        })

        self.assertEqual(response.status_code, 404)

    def test_long_title_truncated_to_attribute_max_length(self):
        # AttributeModel.name has max_length=64; longer titles get
        # truncated rather than rejected so the attach succeeds.
        entity = self._entity()
        long_title = 'X' * 100

        response = self.client.post(self._url(), data={
            WireField.ITEM_TYPE: str(ItemType.ENTITY),
            WireField.ITEM_ID: entity.id,
            WireField.SELECTIONS: json.dumps([{
                WireField.SELECTION_TITLE: long_title,
                WireField.SELECTION_URL: 'https://p/1',
            }]),
        })

        self.assertEqual(response.status_code, 200)
        attr = EntityAttribute.objects.get(entity=entity)
        self.assertEqual(len(attr.name), 64)
        self.assertTrue(attr.name.startswith('X'))
