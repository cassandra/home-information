"""View tests for the EXTERNAL_REFERENCE picker.

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

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location
from hi.enums import ItemType, ViewMode
from hi.integrations.enums import IntegrationAttributeType, IntegrationCapability
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import Integration
from hi.integrations.referencer.integration_referencer import (
    IntegrationExternalReferencer,
)
from hi.constants import DIVID
from hi.integrations.referencer.transient_models import (
    ExternalReferenceResult,
    ExternalReferenceSearchResult,
)
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
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


class _StubReferencer(IntegrationExternalReferencer):
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
        self.attach_calls = []

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self._integration_id,
            label=self._label,
            attribute_type=_RefAttributeType,
            allow_entity_deletion=True,
            capabilities=frozenset({IntegrationCapability.EXTERNAL_REFERENCE}),
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def search_references(self, query, limit=20):
        self.last_query = query
        self.last_limit = limit
        if self._raises is not None:
            raise self._raises
        return ExternalReferenceSearchResult(
            results=list(self._results),
            error_message=self._error_message,
        )

    def attach_references(self, owner, selections):
        # Capture (owner, selections-list) so dispatcher tests can
        # assert grouping and per-call shape.
        self.attach_calls.append((owner, list(selections)))


class _ReferencerCapableGateway(IntegrationGateway):
    """Gateway that advertises EXTERNAL_REFERENCE and returns the
    test's stub referencer from ``get_external_referencer``."""

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
            capabilities=frozenset({IntegrationCapability.EXTERNAL_REFERENCE}),
        )

    def validate_configuration(self, integration_attributes):
        return IntegrationValidationResult.success()

    def validate_access(self, integration_attributes, timeout_secs):
        return ConnectionTestResult.success()

    def get_external_referencer(self):
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
            integration_id='ref', integration_name='doc-1',
            thumbnail_url=None, mime_type=None, snippet=None):
    return ExternalReferenceResult(
        integration_key=IntegrationKey(
            integration_id=integration_id,
            integration_name=integration_name,
        ),
        title=title,
        source_url=source_url,
        thumbnail_url=thumbnail_url,
        mime_type=mime_type,
        snippet=snippet,
    )


# ---- gateway default --------------------------------------------


class TestIntegrationGatewayExternalReferencerDefault(ViewTestBase):
    """Default ``IntegrationGateway`` advertises no EXTERNAL_REFERENCE
    referencer — only integrations that explicitly opt in do."""

    def test_default_returns_none(self):
        self.assertIsNone(IntegrationGateway().get_external_referencer())


# ---- picker GET ----------------------------------------------------


class TestExternalReferencePickerView(ViewTestBase):
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


class TestExternalReferenceSearchView(ViewTestBase):
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


class TestExternalReferenceAttachView(ViewTestBase):
    """POST parses the JS-built ``selections_json`` payload, groups
    selections by integration_id, and dispatches each group to the
    integration's ``attach_references``. Per-row persistence is owned
    by the integration (which writes to the framework's
    EntityExternalReference / LocationExternalReference tables);
    these tests assert the dispatcher's grouping + owner resolution
    + payload-shape contract, not the per-row write."""

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
    def _selection_dict(*, integration_id='ref', integration_name='item-1',
                        title='Title', source_url='https://example.com/1',
                        mime_type='application/pdf'):
        return {
            DIVID['ATTR_PICKER_SELECTION_TITLE_KEY']: title,
            DIVID['ATTR_PICKER_SELECTION_URL_KEY']: source_url,
            DIVID['ATTR_PICKER_SELECTION_INTEGRATION_ID_KEY']: integration_id,
            DIVID['ATTR_PICKER_SELECTION_INTEGRATION_NAME_KEY']: integration_name,
            DIVID['ATTR_PICKER_SELECTION_MIME_TYPE_KEY']: mime_type,
        }

    def _payload(self, owner, selections):
        item_type = ItemType.ENTITY if isinstance(owner, Entity) else ItemType.LOCATION
        return {
            DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(item_type),
            DIVID['ATTR_PICKER_ITEM_ID_FIELD']: owner.id,
            DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: json.dumps(selections),
        }

    def test_attach_dispatches_single_integration_selections(self):
        entity = self._entity()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])

        response = self.client.post(
            self._url(),
            data=self._payload(entity, [
                self._selection_dict(
                    integration_id='paperless',
                    integration_name='42',
                    title='Warranty',
                    source_url='https://p/doc/42',
                ),
                self._selection_dict(
                    integration_id='paperless',
                    integration_name='99',
                    title='Manual',
                    source_url='https://p/doc/99',
                ),
            ]),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content).get('refresh'))
        # One attach call with both selections — grouped by
        # integration_id, the dispatcher hands the whole group at
        # once.
        self.assertEqual(len(ref.attach_calls), 1)
        owner_arg, selections = ref.attach_calls[0]
        self.assertEqual(owner_arg, entity)
        self.assertEqual([s.integration_key.integration_name for s in selections],
                         ['42', '99'])
        self.assertEqual([s.title for s in selections], ['Warranty', 'Manual'])

    def test_attach_groups_by_integration_id(self):
        entity = self._entity()
        ref_a = _StubReferencer(integration_id='paperless', label='Paperless')
        ref_b = _StubReferencer(integration_id='immich', label='Immich')
        _populate_manager([
            ('paperless', _ReferencerCapableGateway(
                integration_id='paperless', label='Paperless', referencer=ref_a,
            )),
            ('immich', _ReferencerCapableGateway(
                integration_id='immich', label='Immich', referencer=ref_b,
            )),
        ])

        self.client.post(
            self._url(),
            data=self._payload(entity, [
                self._selection_dict(
                    integration_id='paperless', integration_name='42'),
                self._selection_dict(
                    integration_id='immich', integration_name='uuid-1'),
                self._selection_dict(
                    integration_id='paperless', integration_name='99'),
            ]),
            **self.async_http_headers,
        )
        # Each integration gets one call with its own selections.
        self.assertEqual(len(ref_a.attach_calls), 1)
        self.assertEqual(len(ref_b.attach_calls), 1)
        self.assertEqual(
            [s.integration_key.integration_name for s in ref_a.attach_calls[0][1]],
            ['42', '99'],
        )
        self.assertEqual(
            [s.integration_key.integration_name for s in ref_b.attach_calls[0][1]],
            ['uuid-1'],
        )

    def test_attach_dispatches_to_location_owner(self):
        location = self._location()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])

        self.client.post(
            self._url(),
            data=self._payload(location, [
                self._selection_dict(
                    integration_id='paperless', integration_name='42'),
            ]),
            **self.async_http_headers,
        )
        self.assertEqual(len(ref.attach_calls), 1)
        self.assertEqual(ref.attach_calls[0][0], location)

    def test_attach_with_empty_selections_calls_nothing(self):
        entity = self._entity()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])
        self.client.post(
            self._url(),
            data=self._payload(entity, []),
            **self.async_http_headers,
        )
        self.assertEqual(ref.attach_calls, [])

    def test_attach_with_malformed_json_calls_nothing(self):
        # Defensive: malformed JSON yields zero dispatches rather
        # than a 500. The JS contract submits valid JSON; this
        # guards against a manual replay.
        entity = self._entity()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])
        payload = self._payload(entity, [])
        payload[DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']] = 'not-json'
        response = self.client.post(
            self._url(), data=payload, **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ref.attach_calls, [])

    def test_attach_skips_selections_with_missing_fields(self):
        entity = self._entity()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])
        # Three records: missing title, missing url, missing integration_name.
        # All should be skipped; nothing dispatches.
        self.client.post(
            self._url(),
            data=self._payload(entity, [
                self._selection_dict(
                    integration_id='paperless', integration_name='1',
                    title=''),
                self._selection_dict(
                    integration_id='paperless', integration_name='2',
                    source_url=''),
                self._selection_dict(
                    integration_id='paperless', integration_name=''),
            ]),
            **self.async_http_headers,
        )
        self.assertEqual(ref.attach_calls, [])

    def test_attach_unknown_integration_id_skips_silently(self):
        # Selection references an integration that has no enabled
        # referencer. Dispatcher logs + skips; no exception bubbles
        # up so the operator's other selections still attach.
        entity = self._entity()
        ref = _StubReferencer(integration_id='paperless')
        _populate_manager([('paperless', _ReferencerCapableGateway(
            integration_id='paperless', referencer=ref,
        ))])
        self.client.post(
            self._url(),
            data=self._payload(entity, [
                self._selection_dict(
                    integration_id='paperless', integration_name='42'),
                self._selection_dict(
                    integration_id='unknown-integration',
                    integration_name='x'),
            ]),
            **self.async_http_headers,
        )
        # The known integration still receives its selection.
        self.assertEqual(len(ref.attach_calls), 1)
        self.assertEqual(
            ref.attach_calls[0][1][0].integration_key.integration_id,
            'paperless',
        )

    def test_attach_unsupported_item_type_returns_400(self):
        response = self.client.post(
            self._url(),
            data={
                DIVID['ATTR_PICKER_ITEM_TYPE_FIELD']: str(ItemType.COLLECTION),
                DIVID['ATTR_PICKER_ITEM_ID_FIELD']: 1,
                DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: json.dumps(
                    [self._selection_dict()]),
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
                DIVID['ATTR_PICKER_SELECTIONS_JSON_FIELD']: json.dumps(
                    [self._selection_dict()]),
            },
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)
