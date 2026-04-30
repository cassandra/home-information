"""
Tests for DispatcherFormParser.

Three-level inheritance (top → group → entity) and skip / new-view
sentinel resolution. Drives the parser directly with a request
factory; doesn't touch the dispatcher view or modal rendering.
"""
import logging

from django.http import QueryDict
from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.integrations.dispatcher_form import DispatcherFormParser

logging.disable(logging.CRITICAL)


class _FakeIntegrationData:
    """Stand-in carrying the only field DispatcherFormParser reads."""
    def __init__(self, label):
        self.label = label
        self.integration_id = 'parser_test'


class _RequestStub:
    """Minimal request-like with a POST QueryDict."""
    def __init__(self, post):
        self.POST = post

    @property
    def view_parameters(self):
        # _create_new_view paths through LocationManager() which
        # doesn't touch view_parameters in its create_location_view
        # branch, but get_default_location does. Tests that exercise
        # the new-view path stub get_default_location instead.
        raise AttributeError('view_parameters not available in stub')


class DispatcherFormParserTests(TestCase):

    def setUp(self):
        self.location = Location.objects.create(
            name='Test', svg_view_box_str='0 0 100 100',
        )
        self.view_a = LocationView.objects.create(
            location=self.location, name='Kitchen', order_id=1,
            svg_view_box_str='0 0 100 100', svg_rotate=0,
            svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
        )
        self.view_b = LocationView.objects.create(
            location=self.location, name='Living Room', order_id=2,
            svg_view_box_str='0 0 100 100', svg_rotate=0,
            svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
        )
        self.entity_a = Entity.objects.create(
            name='Cam 1', entity_type_str=str(EntityType.CAMERA),
            integration_id='parser_test', integration_name='cam_1',
        )
        self.entity_b = Entity.objects.create(
            name='Cam 2', entity_type_str=str(EntityType.CAMERA),
            integration_id='parser_test', integration_name='cam_2',
        )
        self.ungrouped_entity = Entity.objects.create(
            name='Thing', entity_type_str=str(EntityType.OTHER),
            integration_id='parser_test', integration_name='thing_1',
        )
        self.integration_data = _FakeIntegrationData(label='Parser Test')

    def _post(self, **fields):
        qd = QueryDict(mutable=True)
        for key, value in fields.items():
            if isinstance(value, list):
                qd.setlist(key, value)
            else:
                qd[key] = value
        return _RequestStub(post=qd)

    def test_top_inherits_to_groups_and_entities(self):
        request = self._post(
            top_view=f'view:{self.view_a.id}',
            all_group_0_entity_ids=[str(self.entity_a.id), str(self.entity_b.id)],
        )
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertEqual(len(decisions), 2)
        for d in decisions:
            self.assertEqual(d.location_view, self.view_a)

    def test_group_overrides_top(self):
        request = self._post(**{
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
            'group_view_0': f'view:{self.view_b.id}',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertEqual(decisions[0].location_view, self.view_b)

    def test_entity_overrides_group(self):
        request = self._post(**{
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'group_view_0': f'view:{self.view_a.id}',
            f'group_0_entity_{self.entity_b.id}_view': f'view:{self.view_b.id}',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        by_entity = {d.entity.id: d.location_view for d in decisions}
        self.assertEqual(by_entity[self.entity_a.id], self.view_a)
        self.assertEqual(by_entity[self.entity_b.id], self.view_b)

    def test_explicit_skip_at_group_overrides_top(self):
        request = self._post(**{
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
            'group_view_0': '__skip__',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertIsNone(decisions[0].location_view)

    def test_explicit_skip_at_entity_overrides_group(self):
        request = self._post(**{
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            f'group_0_entity_{self.entity_a.id}_view': '__skip__',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        by_entity = {d.entity.id: d.location_view for d in decisions}
        self.assertIsNone(by_entity[self.entity_a.id])
        self.assertEqual(by_entity[self.entity_b.id], self.view_a)

    def test_skip_all_at_top(self):
        request = self._post(
            top_view='',
            all_group_0_entity_ids=[str(self.entity_a.id)],
        )
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertIsNone(decisions[0].location_view)

    def test_ungrouped_inherits_from_top(self):
        request = self._post(
            top_view=f'view:{self.view_a.id}',
            ungrouped_entity_ids=[str(self.ungrouped_entity.id)],
        )
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertEqual(decisions[0].entity, self.ungrouped_entity)
        self.assertEqual(decisions[0].location_view, self.view_a)

    def test_ungrouped_entity_override_wins(self):
        request = self._post(**{
            'top_view': f'view:{self.view_a.id}',
            'ungrouped_entity_ids': [str(self.ungrouped_entity.id)],
            f'ungrouped_entity_{self.ungrouped_entity.id}_view': f'view:{self.view_b.id}',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertEqual(decisions[0].location_view, self.view_b)

    def test_collection_target_via_top(self):
        """Top dropdown's existing-collection option routes inherited
        entities to that Collection, not a LocationView."""
        from hi.apps.collection.enums import CollectionType, CollectionViewType
        from hi.apps.collection.models import Collection
        collection = Collection(
            name='Tools', order_id=0,
        )
        collection.collection_type = CollectionType.default()
        collection.collection_view_type = CollectionViewType.default()
        collection.save()

        request = self._post(
            top_view=f'collection:{collection.id}',
            all_group_0_entity_ids=[str(self.entity_a.id)],
        )
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        self.assertIsNone(decisions[0].location_view)
        self.assertEqual(decisions[0].collection, collection)

    def test_mixed_view_and_collection_targets(self):
        """One group routes to a LocationView; another routes to a
        Collection — both targets coexist in the same submission."""
        from hi.apps.collection.enums import CollectionType, CollectionViewType
        from hi.apps.collection.models import Collection
        collection = Collection(name='Tools', order_id=0)
        collection.collection_type = CollectionType.default()
        collection.collection_view_type = CollectionViewType.default()
        collection.save()

        request = self._post(**{
            'top_view': '',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
            'group_view_0': f'view:{self.view_a.id}',
            'all_group_1_entity_ids': [str(self.entity_b.id)],
            'group_view_1': f'collection:{collection.id}',
        })
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        by_entity = {d.entity.id: d for d in decisions}
        self.assertEqual(by_entity[self.entity_a.id].location_view, self.view_a)
        self.assertIsNone(by_entity[self.entity_a.id].collection)
        self.assertEqual(by_entity[self.entity_b.id].collection, collection)
        self.assertIsNone(by_entity[self.entity_b.id].location_view)

    def test_new_collection_creates_collection_and_inherits_to_entities(self):
        """top='__new_collection__' creates a fresh Collection named
        after the integration label; entities inherit that target."""
        from hi.apps.collection.models import Collection
        before_ids = set(Collection.objects.values_list('id', flat=True))
        request = self._post(
            top_view='__new_collection__',
            all_group_0_entity_ids=[str(self.entity_a.id)],
        )
        decisions = DispatcherFormParser.parse(
            request=request, integration_data=self.integration_data,
        )
        new_ids = (
            set(Collection.objects.values_list('id', flat=True)) - before_ids
        )
        self.assertEqual(len(new_ids), 1)
        new_collection = Collection.objects.get(id=new_ids.pop())
        self.assertEqual(new_collection.name, 'Parser Test')
        self.assertEqual(decisions[0].collection, new_collection)
        self.assertIsNone(decisions[0].location_view)

    def test_new_view_creates_view_and_inherits_to_entities(self):
        from unittest.mock import patch
        request = self._post(
            top_view='__new_view__',
            all_group_0_entity_ids=[str(self.entity_a.id)],
        )
        # _create_new_view ultimately calls
        # LocationManager().get_default_location(request) → must be
        # patched because the request stub doesn't carry session
        # state. The patched return is the test's existing Location;
        # the parser then creates a real LocationView attached to it.
        with patch(
            'hi.integrations.dispatcher_form.LocationManager',
        ) as mock_manager_cls:
            instance = mock_manager_cls.return_value
            instance.get_default_location.return_value = self.location
            new_view = LocationView.objects.create(
                location=self.location, name='Parser Test', order_id=99,
                svg_view_box_str='0 0 100 100', svg_rotate=0,
                svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
            )
            instance.create_location_view.return_value = new_view

            decisions = DispatcherFormParser.parse(
                request=request, integration_data=self.integration_data,
            )

        self.assertEqual(decisions[0].location_view, new_view)
        # The factory was called with the integration label.
        instance.create_location_view.assert_called_once_with(
            location=self.location, name='Parser Test',
        )
