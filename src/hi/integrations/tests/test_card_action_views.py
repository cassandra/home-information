"""View tests for the per-card external-reference action endpoints
(rename, delete, reorder). Each view POSTs and responds with the
freshly-rendered grid HTML; the JS layer swaps the response in
place via ``$grid.replaceWith(html)``.

Focus is the branching logic: title validation, direction
validation, sibling re-order arithmetic, and the 404 path through
``get_external_reference_or_404``. The grid-render response shape
is asserted at the integration boundary (presence of the grid div
id) rather than re-asserting full HTML.
"""
import logging

from django.urls import reverse

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location
from hi.enums import ViewMode
from hi.integrations.models import (
    EntityExternalReference,
    LocationExternalReference,
)
from hi.testing.view_test_base import ViewTestBase


logging.disable(logging.CRITICAL)


def _make_entity(name='Dishwasher'):
    return Entity.objects.create(
        name=name,
        entity_type_str=str(EntityType.DISHWASHER),
    )


def _make_location(name='Kitchen'):
    return Location.objects.create(
        name=name,
        svg_fragment_filename='kitchen.svg',
        svg_view_box_str='0 0 100 100',
    )


def _make_entity_ref(entity, *, integration_name='doc-1', title='Doc',
                     order_id=0):
    return EntityExternalReference.objects.create(
        entity=entity,
        integration_id='ref',
        integration_name=integration_name,
        title=title,
        source_url=f'https://example.com/{integration_name}',
        order_id=order_id,
    )


# ---- rename ------------------------------------------------------


class TestExternalReferenceRenameView(ViewTestBase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)
        self.entity = _make_entity()

    def _url(self, reference, owner_type='entity'):
        return reverse('external_reference_rename', kwargs={
            'owner_type': owner_type,
            'reference_id': reference.id,
        })

    def test_rename_updates_title_and_returns_grid_html(self):
        ref = _make_entity_ref(self.entity, title='Old')
        response = self.client.post(
            self._url(ref), data={'title': 'New Title'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        ref.refresh_from_db()
        self.assertEqual(ref.title, 'New Title')
        # Response carries the rendered grid for the owner.
        self.assertIn(
            f'hi-ext-ref-grid-entity-{self.entity.id}',
            response.content.decode(),
        )

    def test_rename_empty_title_returns_400(self):
        ref = _make_entity_ref(self.entity, title='Old')
        response = self.client.post(
            self._url(ref), data={'title': '   '},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)
        ref.refresh_from_db()
        self.assertEqual(ref.title, 'Old')

    def test_rename_truncates_long_title_to_255_chars(self):
        ref = _make_entity_ref(self.entity)
        long_title = 'x' * 500
        self.client.post(
            self._url(ref), data={'title': long_title},
            **self.async_http_headers,
        )
        ref.refresh_from_db()
        self.assertEqual(len(ref.title), 255)

    def test_rename_unknown_owner_type_returns_404(self):
        ref = _make_entity_ref(self.entity)
        response = self.client.post(
            self._url(ref, owner_type='nonsense'),
            data={'title': 'X'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_rename_missing_reference_returns_404(self):
        url = reverse('external_reference_rename', kwargs={
            'owner_type': 'entity', 'reference_id': 99999,
        })
        response = self.client.post(
            url, data={'title': 'X'}, **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 404)


# ---- delete ------------------------------------------------------


class TestExternalReferenceDeleteView(ViewTestBase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)

    def _url(self, reference, owner_type='entity'):
        return reverse('external_reference_delete', kwargs={
            'owner_type': owner_type,
            'reference_id': reference.id,
        })

    def test_delete_removes_row_and_returns_grid_html(self):
        entity = _make_entity()
        ref = _make_entity_ref(entity)
        _make_entity_ref(
            entity, integration_name='doc-2', title='Survivor',
        )
        response = self.client.post(
            self._url(ref), **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            EntityExternalReference.objects.filter(pk=ref.pk).exists()
        )
        # Sibling and the freshly-rendered grid for the owner survive.
        body = response.content.decode()
        self.assertIn(f'hi-ext-ref-grid-entity-{entity.id}', body)
        self.assertIn('Survivor', body)

    def test_delete_for_location_owner(self):
        location = _make_location()
        ref = LocationExternalReference.objects.create(
            location=location,
            integration_id='ref',
            integration_name='asset-1',
            title='Photo',
            source_url='https://example.com/asset-1',
        )
        response = self.client.post(
            self._url(ref, owner_type='location'),
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            LocationExternalReference.objects.filter(pk=ref.pk).exists()
        )
        self.assertIn(
            f'hi-ext-ref-grid-location-{location.id}',
            response.content.decode(),
        )


# ---- reorder -----------------------------------------------------


class TestExternalReferenceReorderView(ViewTestBase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.setSessionViewMode(ViewMode.EDIT)
        self.entity = _make_entity()
        # Three siblings with explicit order_ids so the test reads as
        # "the second one moves" rather than relying on insert order.
        self.r0 = _make_entity_ref(
            self.entity, integration_name='a', title='A', order_id=0,
        )
        self.r1 = _make_entity_ref(
            self.entity, integration_name='b', title='B', order_id=1,
        )
        self.r2 = _make_entity_ref(
            self.entity, integration_name='c', title='C', order_id=2,
        )

    def _url(self, reference):
        return reverse('external_reference_reorder', kwargs={
            'owner_type': 'entity',
            'reference_id': reference.id,
        })

    def _current_order(self):
        return list(
            EntityExternalReference.objects
            .filter(entity=self.entity)
            .order_by('order_id', '-created_datetime')
            .values_list('title', flat=True)
        )

    def test_reorder_left_swaps_with_previous_sibling(self):
        response = self.client.post(
            self._url(self.r1), data={'direction': 'left'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._current_order(), ['B', 'A', 'C'])

    def test_reorder_right_swaps_with_next_sibling(self):
        response = self.client.post(
            self._url(self.r1), data={'direction': 'right'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._current_order(), ['A', 'C', 'B'])

    def test_reorder_left_at_first_position_is_noop(self):
        response = self.client.post(
            self._url(self.r0), data={'direction': 'left'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._current_order(), ['A', 'B', 'C'])

    def test_reorder_renormalizes_order_ids_to_dense_sequence(self):
        # Start with sparse / non-zero-based order_ids; a swap should
        # leave the affected rows densely numbered 0..N-1.
        for ref, sparse in ((self.r0, 10), (self.r1, 20), (self.r2, 30)):
            ref.order_id = sparse
            ref.save(update_fields=['order_id'])
        self.client.post(
            self._url(self.r1), data={'direction': 'left'},
            **self.async_http_headers,
        )
        order_ids = sorted(
            EntityExternalReference.objects
            .filter(entity=self.entity)
            .values_list('order_id', flat=True)
        )
        self.assertEqual(order_ids, [0, 1, 2])

    def test_reorder_invalid_direction_returns_400(self):
        response = self.client.post(
            self._url(self.r1), data={'direction': 'sideways'},
            **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._current_order(), ['A', 'B', 'C'])

    def test_reorder_missing_direction_returns_400(self):
        response = self.client.post(
            self._url(self.r1), **self.async_http_headers,
        )
        self.assertEqual(response.status_code, 400)
