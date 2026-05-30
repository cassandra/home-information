"""View tests for the ATTRIBUTE_REFERENCE picker.

The picker is split into three endpoints:

  - ``integrations_attribute_reference_picker`` — GET, renders the
    initial empty modal.
  - ``integrations_attribute_reference_search`` — POST, returns the
    result-cards partial. The attr-picker.js module swaps the
    returned HTML into the picker's results container.
  - ``integrations_attribute_reference_attach`` — POST, reads the
    JS-built ``selections_json`` payload, creates one TEXT
    attribute per record, returns ``antinode.refresh_response()``.

Selection state lives in JS during the session; the server is
consulted only at search time (per-query) and at attach time (the
single final commit).
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
from hi.integrations.referencer.integration_referencer import (
    IntegrationAttributeReferencer,
)
from hi.constants import DIVID
from hi.integrations.referencer.transient_models import (
    AttributeReferenceResult,
    AttributeReferenceSearchResult,
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
    Captures search args so tests can assert dispatch shape."""

    def __init__(self, integration_id='ref', label='Ref Test',
                 results=None, raises=None, error_message=None):
        self._integration_id = integration_id
        self._label = label
        self._results = results or []
        self._raises = raises
        self._error_message = error_message
        self.last_query = None
        self.last_limit = None

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self._integration_id,
            label=self._label,
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
        return AttributeReferenceSearchResult(
            results=list(self._results),
            error_message=self._error_message,
        )


class _ReferencerCapableGateway(IntegrationGateway):
    """Gateway that advertises ATTRIBUTE_REFERENCE and returns the
    test's stub referencer from ``get_attribute_referencer``."""

    def __init__(self, integration_id='ref', label='Ref Test', referencer=None):
        self.integration_id = integration_id
        self.label = label
        self._referencer = referencer

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label=self.label,
            attribute_type=_RefAttributeType,
            allow_entity_deletion=True,
            capabilities=frozenset({IntegrationCapability.ATTRIBUTE_REFERENCE}),
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def validate_access(self, integration_attributes, timeout_secs):
        return ConnectionTestResult.success()

    def get_attribute_referencer(self):
        return self._referencer


def _populate_manager(pairs, enabled=True):
    """Seed the IntegrationManager with the given (id, gateway) pairs.
    By default the integrations are marked enabled so the picker view
    sees them through its ``enabled_only=True`` filter."""
    manager = IntegrationManager()
    manager._integration_data_map = {}
    for integration_id, gateway in pairs:
        integration, _ = Integration.objects.get_or_create(
            integration_id=integration_id,
            defaults={'is_enabled': enabled},
        )
        if integration.is_enabled != enabled:
            integration.is_enabled = enabled
            integration.save()
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
    """Default ``IntegrationGateway`` advertises no ATTRIBUTE_REFERENCE
    referencer — only integrations that explicitly opt in do."""

    def test_default_returns_none(self):
        self.assertIsNone(IntegrationGateway().get_attribute_referencer())


# ---- picker GET ----------------------------------------------------


class TestAttributeReferencePickerView(ViewTestBase):
    """GET renders the initial empty modal. Search and attach are
    sibling endpoints (tested separately below)."""

    INTEGRATION_ID = 'ref'

    def setUp(self):
        super().setUp()
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)
        self.referencer = _StubReferencer(integration_id=self.INTEGRATION_ID)
        self.gateway = _ReferencerCapableGateway(
            self.INTEGRATION_ID, referencer=self.referencer,
        )
        _populate_manager([(self.INTEGRATION_ID, self.gateway)])

    def _entity(self, name='Dishwasher'):
        return Entity.objects.create(
            name=name,
            entity_type_str=str(EntityType.DISHWASHER),
        )

    def _url(self):
        return reverse('integrations_attribute_reference_picker')

    def test_get_renders_modal_with_integration_label(self):
        entity = self._entity()
        response = self.client.get(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.ENTITY),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: entity.id,
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ref Test', response.content.decode())

    def test_get_with_no_enabled_referencer_returns_404(self):
        _populate_manager([])
        entity = self._entity()
        response = self.client.get(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.ENTITY),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: entity.id,
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_get_unknown_item_type_returns_400(self):
        response = self.client.get(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: 'banana',
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: 1,
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_get_missing_owner_returns_404(self):
        response = self.client.get(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.ENTITY),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: 99999,
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_get_with_multiple_referencers_renders_selector(self):
        other_ref = _StubReferencer(integration_id='other', label='Other Ref')
        other_gw = _ReferencerCapableGateway(
            'other', label='Other Ref', referencer=other_ref,
        )
        _populate_manager([
            (self.INTEGRATION_ID, self.gateway),
            ('other', other_gw),
        ])
        entity = self._entity()
        response = self.client.get(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.ENTITY),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: entity.id,
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        decoded = response.content.decode()
        self.assertIn('Ref Test', decoded)
        self.assertIn('Other Ref', decoded)


# ---- search endpoint ----------------------------------------------


class TestAttributeReferenceSearchView(ViewTestBase):
    """POST returns the result-cards partial. The picker JS swaps
    the returned HTML into the results container."""

    INTEGRATION_ID = 'ref'

    def setUp(self):
        super().setUp()
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)
        self.referencer = _StubReferencer(integration_id=self.INTEGRATION_ID)
        self.gateway = _ReferencerCapableGateway(
            self.INTEGRATION_ID, referencer=self.referencer,
        )
        _populate_manager([(self.INTEGRATION_ID, self.gateway)])

    def _url(self):
        return reverse('integrations_attribute_reference_search')

    def _payload(self, query='', limit=20, integration_id=None):
        return {
            DIVID['ATTR_PICKER_QUERY_FIELD']: query,
            DIVID['ATTR_PICKER_LIMIT_FIELD']: str(limit),
            DIVID['ATTR_PICKER_INTEGRATION_ID_FIELD']: integration_id or self.INTEGRATION_ID,
        }

    def test_empty_query_does_not_call_referencer(self):
        response = self.client.post(
            self._url(),
            data=self._payload(query='   '),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.referencer.last_query)

    def test_search_dispatches_with_clamped_limit(self):
        self.referencer._results = [_result()]
        response = self.client.post(
            self._url(),
            data=self._payload(query='dishwasher', limit=50),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.referencer.last_query, 'dishwasher')
        self.assertEqual(self.referencer.last_limit, 50)

    def test_search_returns_result_cards_html(self):
        self.referencer._results = [
            _result(title='Warranty', source_url='https://p/doc/1'),
            _result(title='Manual', source_url='https://p/doc/2'),
        ]
        response = self.client.post(
            self._url(),
            data=self._payload(query='dishwasher'),
            **self.async_http_headers,
        )
        body = response.content.decode()
        self.assertIn('Warranty', body)
        self.assertIn('Manual', body)
        self.assertIn('https://p/doc/1', body)
        # Cards carry data attributes so JS can read title + URL on
        # checkbox change without parsing the DOM.
        self.assertIn('data-attr-picker-source-url', body)
        self.assertIn('data-attr-picker-title', body)

    def test_search_with_no_results_returns_empty_message(self):
        self.referencer._results = []
        response = self.client.post(
            self._url(),
            data=self._payload(query='nothing-matches'),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('No results', response.content.decode())

    def test_search_invalid_limit_falls_back_to_default(self):
        self.referencer._results = [_result()]
        payload = self._payload(query='q')
        payload[DIVID['ATTR_PICKER_LIMIT_FIELD']] = 'not-a-number'
        self.client.post(
            self._url(), data=payload, **self.async_http_headers,
        )
        self.assertEqual(self.referencer.last_limit, 20)

    def test_search_unknown_integration_id_returns_400(self):
        response = self.client.post(
            self._url(),
            data=self._payload(query='q', integration_id='nope'),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_search_referencer_exception_renders_labeled_banner(self):
        # Raised exceptions are the "referencer is broken" path; the
        # framework catches and surfaces a banner naming the
        # integration so the picker stays usable and the operator
        # knows which referencer to look at.
        self.referencer._raises = RuntimeError('upstream down')
        response = self.client.post(
            self._url(),
            data=self._payload(query='q'),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Ref Test search failed', body)
        self.assertNotIn('No results', body)

    def test_search_referencer_error_message_renders_banner(self):
        # Referencers that populate ``error_message`` instead of
        # raising should also surface as a banner, not "no results".
        self.referencer._error_message = 'Upstream auth rejected.'
        response = self.client.post(
            self._url(),
            data=self._payload(query='q'),
            **self.async_http_headers,
        )
        body = response.content.decode()
        self.assertIn('Upstream auth rejected.', body)
        self.assertNotIn('No results', body)


# ---- attach endpoint ----------------------------------------------


class TestAttributeReferenceAttachView(ViewTestBase):
    """POST reads the JS-built ``selections_json`` payload and
    creates one TEXT attribute per record on the named owner."""

    def setUp(self):
        super().setUp()
        IntegrationManager()._instances = {}
        IntegrationManager._initialized_instance = None
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)

    def _url(self):
        return reverse('integrations_attribute_reference_attach')

    @staticmethod
    def _entity(name='Dishwasher'):
        return Entity.objects.create(
            name=name,
            entity_type_str=str(EntityType.DISHWASHER),
        )

    @staticmethod
    def _location(name='Kitchen'):
        return Location.objects.create(
            name=name,
            svg_fragment_filename='kitchen.svg',
            svg_view_box_str='0 0 100 100',
        )

    @staticmethod
    def _selections_json(*pairs):
        return json.dumps([
            {DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: title, DIVID['ATTR_PICKER_SELECTION_URL_KEY']: url}
            for title, url in pairs
        ])

    def _payload(self, owner, selections_json):
        item_type = ItemType.ENTITY if isinstance(owner, Entity) else ItemType.LOCATION
        return {
            DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(item_type),
            DIVID['ATTR_PICKER_ITEM_ID_FIELD']: owner.id,
            DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: selections_json,
        }

    def test_attach_creates_text_attributes_on_entity(self):
        entity = self._entity()
        response = self.client.post(
            self._url(),
            data=self._payload(entity, self._selections_json(
                ('Warranty', 'https://p/doc/1'),
                ('Manual', 'https://p/doc/2'),
            )),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body.get('refresh'))

        attrs = list(EntityAttribute.objects.filter(entity=entity).order_by('id'))
        self.assertEqual(len(attrs), 2)
        self.assertEqual(attrs[0].name, 'Warranty')
        self.assertEqual(attrs[0].value, 'https://p/doc/1')
        self.assertEqual(attrs[0].value_type, AttributeValueType.TEXT)
        self.assertEqual(attrs[0].attribute_type, AttributeType.CUSTOM)
        self.assertEqual(attrs[1].name, 'Manual')

    def test_attach_creates_text_attribute_on_location(self):
        location = self._location()
        response = self.client.post(
            self._url(),
            data=self._payload(location, self._selections_json(
                ('Floor Plan', 'https://p/doc/floor-plan'),
            )),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        attrs = list(LocationAttribute.objects.filter(location=location))
        self.assertEqual(len(attrs), 1)
        self.assertEqual(attrs[0].name, 'Floor Plan')

    def test_attach_with_empty_selections_creates_nothing(self):
        entity = self._entity()
        response = self.client.post(
            self._url(),
            data=self._payload(entity, json.dumps([])),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EntityAttribute.objects.filter(entity=entity).count(), 0,
        )

    def test_attach_with_malformed_json_creates_nothing(self):
        # Defensive: malformed JSON yields no attributes rather than
        # a 500. The JS contract submits valid JSON; this guards
        # against a manual replay.
        entity = self._entity()
        response = self.client.post(
            self._url(),
            data=self._payload(entity, 'not-json'),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EntityAttribute.objects.filter(entity=entity).count(), 0,
        )

    def test_attach_skips_records_with_missing_fields(self):
        entity = self._entity()
        payload = self._payload(entity, json.dumps([
            {DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: '', DIVID['ATTR_PICKER_SELECTION_URL_KEY']: 'https://p/1'},
            {DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: 'Good', DIVID['ATTR_PICKER_SELECTION_URL_KEY']: 'https://p/2'},
            {DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: 'No URL', DIVID['ATTR_PICKER_SELECTION_URL_KEY']: ''},
        ]))
        self.client.post(self._url(), data=payload, **self.async_http_headers)
        attrs = list(EntityAttribute.objects.filter(entity=entity).order_by('id'))
        self.assertEqual(len(attrs), 1)
        self.assertEqual(attrs[0].name, 'Good')

    def test_attach_long_title_truncated_to_max_length(self):
        entity = self._entity()
        long_title = 'X' * 100
        payload = self._payload(entity, json.dumps([{
            DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: long_title,
            DIVID['ATTR_PICKER_SELECTION_URL_KEY']: 'https://p/1',
        }]))
        response = self.client.post(
            self._url(), data=payload, **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        attr = EntityAttribute.objects.get(entity=entity)
        self.assertEqual(len(attr.name), 64)

    def test_attach_unsupported_item_type_returns_400(self):
        response = self.client.post(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.COLLECTION),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: 1,
                DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: self._selections_json(('A', 'https://p/1')),
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_attach_unknown_owner_returns_404(self):
        response = self.client.post(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.ENTITY),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: 99999,
                DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: self._selections_json(('A', 'https://p/1')),
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)
