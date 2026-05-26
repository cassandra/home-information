"""View tests for the ATTRIBUTE_REFERENCE picker (HiModal + antinode).

The picker is a single HiModalView backed by server-driven multi-select:
the form carries the canonical selections list across re-renders and
the view computes the new list each POST from existing + checked -
unchecked-visible (- explicit chip removals).
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
    Captures search args so tests can assert dispatch shape."""

    def __init__(self, integration_id='ref', label='Ref Test',
                 results=None, raises=None):
        self._integration_id = integration_id
        self._label = label
        self._results = results or []
        self._raises = raises
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
        return list(self._results)


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


# ---- picker view ------------------------------------------------


class TestAttributeReferencePickerView(ViewTestBase):

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

    @property
    def _url(self):
        return reverse('integrations_attribute_reference_picker')

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

    @staticmethod
    def _selections_json(*pairs):
        return json.dumps([
            {WireField.SELECTION_TITLE: title, WireField.SELECTION_URL: url}
            for title, url in pairs
        ])

    # -- GET (initial modal) ---------------------------------------

    def test_get_renders_modal_with_integration_label(self):
        entity = self._entity()

        response = self.client.get(
            self._url,
            data={
                WireField.ITEM_TYPE: str(ItemType.ENTITY),
                WireField.ITEM_ID: entity.id,
            },
            **self.async_http_headers,
        )

        self.assertEqual(response.status_code, 200)
        # The modal body carries the integration label so the operator
        # can see which corpus they're searching.
        self.assertIn('Ref Test', response.content.decode())

    def test_get_with_no_enabled_referencer_returns_404(self):
        _populate_manager([])
        entity = self._entity()

        response = self.client.get(
            self._url,
            data={
                WireField.ITEM_TYPE: str(ItemType.ENTITY),
                WireField.ITEM_ID: entity.id,
            },
            **self.async_http_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_get_unknown_item_type_returns_400(self):
        response = self.client.get(
            self._url,
            data={
                WireField.ITEM_TYPE: 'banana',
                WireField.ITEM_ID: 1,
            },
            **self.async_http_headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_get_missing_owner_returns_404(self):
        response = self.client.get(
            self._url,
            data={
                WireField.ITEM_TYPE: str(ItemType.ENTITY),
                WireField.ITEM_ID: 99999,
            },
            **self.async_http_headers,
        )

        self.assertEqual(response.status_code, 404)

    # -- POST (search re-render) -----------------------------------

    def _base_post_data(self, owner, integration_id=None):
        item_type = ItemType.ENTITY if isinstance(owner, Entity) else ItemType.LOCATION
        return {
            WireField.ITEM_TYPE: str(item_type),
            WireField.ITEM_ID: owner.id,
            WireField.INTEGRATION_ID: integration_id or self.INTEGRATION_ID,
            WireField.SELECTIONS_JSON: json.dumps([]),
        }

    def test_post_empty_query_does_not_call_referencer(self):
        # An empty / whitespace query short-circuits to ``[]`` and
        # avoids calling the integration. Saves an upstream round-trip
        # while the operator is still typing.
        entity = self._entity()
        data = self._base_post_data(entity)
        data[WireField.QUERY] = '   '

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.referencer.last_query)

    def test_post_search_dispatches_with_clamped_limit(self):
        self.referencer._results = [_result()]
        entity = self._entity()
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'dishwasher'
        data[WireField.LIMIT] = '50'

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.referencer.last_query, 'dishwasher')
        self.assertEqual(self.referencer.last_limit, 50)

    def test_post_invalid_limit_falls_back_to_default(self):
        self.referencer._results = [_result()]
        entity = self._entity()
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'
        data[WireField.LIMIT] = 'not-a-number'

        self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(self.referencer.last_limit, 20)

    def test_post_referencer_exception_returns_empty_results(self):
        # Upstream errors are caught and surfaced as an empty result
        # set — the modal stays open so the operator can re-search
        # without losing already-selected references.
        self.referencer._raises = RuntimeError('upstream down')
        entity = self._entity()
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)

    def test_post_unknown_integration_id_returns_400(self):
        entity = self._entity()
        data = self._base_post_data(entity, integration_id='nope')
        data[WireField.QUERY] = 'q'

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 400)

    # -- POST (attach) ---------------------------------------------

    def test_attach_creates_text_attributes_on_entity(self):
        entity = self._entity()
        self.referencer._results = [
            _result(title='Warranty', source_url='https://p/doc/1'),
            _result(title='Manual', source_url='https://p/doc/2'),
        ]
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'dishwasher'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Warranty', 'https://p/doc/1'),
            ('Manual', 'https://p/doc/2'),
        )
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        # Attach returns the antinode refresh signal so the parent
        # page reloads and the modal closes.
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
        self.referencer._results = [
            _result(title='Floor Plan', source_url='https://p/doc/floor-plan'),
        ]
        data = self._base_post_data(location)
        data[WireField.QUERY] = 'kitchen'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Floor Plan', 'https://p/doc/floor-plan'),
        )
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        attrs = list(LocationAttribute.objects.filter(location=location))
        self.assertEqual(len(attrs), 1)
        self.assertEqual(attrs[0].name, 'Floor Plan')
        self.assertEqual(attrs[0].value, 'https://p/doc/floor-plan')

    def test_attach_with_empty_selections_creates_nothing(self):
        entity = self._entity()
        data = self._base_post_data(entity)
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EntityAttribute.objects.filter(entity=entity).count(), 0,
        )

    def test_attach_long_title_truncated_to_attribute_max_length(self):
        # AttributeModel.name has max_length=64; longer titles get
        # truncated rather than rejected so the attach succeeds.
        entity = self._entity()
        long_title = 'X' * 100
        self.referencer._results = [_result(
            title=long_title, source_url='https://p/1',
        )]
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            (long_title, 'https://p/1'),
        )
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 200)
        attr = EntityAttribute.objects.get(entity=entity)
        self.assertEqual(len(attr.name), 64)
        self.assertTrue(attr.name.startswith('X'))

    # -- multi-select state ----------------------------------------

    def test_newly_checked_result_added_to_selections(self):
        # Existing selections carry forward; a newly-checked visible
        # URL gets appended using the search result's title.
        entity = self._entity()
        self.referencer._results = [
            _result(title='New Doc', source_url='https://p/new'),
        ]
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Existing', 'https://p/existing'),
        )
        data[WireField.VISIBLE_URL] = 'https://p/new'
        data[WireField.RESULT_URL] = 'https://p/new'
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        self.client.post(self._url, data=data, **self.async_http_headers)

        attrs = set(
            EntityAttribute.objects.filter(entity=entity).values_list('name', flat=True)
        )
        self.assertEqual(attrs, {'Existing', 'New Doc'})

    def test_unchecked_visible_dropped_from_selections(self):
        # If a previously-selected URL is rendered as a visible result
        # but unchecked, the view drops it. (Distinguishes "unchecked"
        # from "no longer visible after a new search".)
        entity = self._entity()
        self.referencer._results = [
            _result(title='Keep Me', source_url='https://p/keep'),
        ]
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Keep Me', 'https://p/keep'),
        )
        # Card is visible but checkbox is not in POST → operator
        # unchecked it.
        data[WireField.VISIBLE_URL] = 'https://p/keep'
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(
            EntityAttribute.objects.filter(entity=entity).count(), 0,
        )

    def test_remove_url_chip_removes_selection(self):
        # The chip × button posts ``remove_url`` to drop a single
        # selection. Distinct from unchecking because chips show
        # selections that aren't in the current result page.
        entity = self._entity()
        self.referencer._results = []
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'q'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Keep', 'https://p/keep'),
            ('Drop', 'https://p/drop'),
        )
        data[WireField.REMOVE_URL] = 'https://p/drop'
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        self.client.post(self._url, data=data, **self.async_http_headers)

        attrs = set(
            EntityAttribute.objects.filter(entity=entity).values_list('name', flat=True)
        )
        self.assertEqual(attrs, {'Keep'})

    def test_selection_outside_current_results_persists_across_search(self):
        # Picking from page 1, then re-searching to page 2 must keep
        # the page-1 pick. The unselected page-1 URL is not in the
        # new visible set, so it isn't dropped.
        entity = self._entity()
        self.referencer._results = [
            _result(title='Page Two Hit', source_url='https://p/p2'),
        ]
        data = self._base_post_data(entity)
        data[WireField.QUERY] = 'new search'
        data[WireField.SELECTIONS_JSON] = self._selections_json(
            ('Page One Pick', 'https://p/p1'),
        )
        data[WireField.VISIBLE_URL] = 'https://p/p2'
        data[WireField.ACTION] = WireField.ACTION_ATTACH

        self.client.post(self._url, data=data, **self.async_http_headers)

        attrs = set(
            EntityAttribute.objects.filter(entity=entity).values_list('name', flat=True)
        )
        self.assertEqual(attrs, {'Page One Pick'})

    # -- multi-integration -----------------------------------------

    def test_get_with_multiple_referencers_renders_selector(self):
        # When more than one referencer is enabled, the picker body
        # should render the integration selector instead of a generic
        # single-integration title.
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
            self._url,
            data={
                WireField.ITEM_TYPE: str(ItemType.ENTITY),
                WireField.ITEM_ID: entity.id,
            },
            **self.async_http_headers,
        )

        self.assertEqual(response.status_code, 200)
        decoded = response.content.decode()
        # Both labels appear as options in the selector.
        self.assertIn('Ref Test', decoded)
        self.assertIn('Other Ref', decoded)

    def test_post_with_disabled_integration_id_returns_400(self):
        # A stale modal must not drive a search against an integration
        # the operator has since disabled. Here ``other`` is in the DB
        # but not enabled, so the picker view's ``enabled_only`` filter
        # excludes it and the POST is rejected.
        other_ref = _StubReferencer(integration_id='other', label='Other Ref')
        other_gw = _ReferencerCapableGateway(
            'other', label='Other Ref', referencer=other_ref,
        )
        # Seed both, but the second is disabled.
        manager = IntegrationManager()
        manager._integration_data_map = {}
        for integration_id, gateway, enabled in [
            (self.INTEGRATION_ID, self.gateway, True),
            ('other', other_gw, False),
        ]:
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
        entity = self._entity()
        data = self._base_post_data(entity, integration_id='other')
        data[WireField.QUERY] = 'q'

        response = self.client.post(self._url, data=data, **self.async_http_headers)

        self.assertEqual(response.status_code, 400)
