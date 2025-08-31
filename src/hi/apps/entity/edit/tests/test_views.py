import logging

from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection, CollectionEntity
from hi.apps.entity.edit.views import ManagePairingsView
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.entity_pairing_manager import EntityPairingManager
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityPosition, EntityStateDelegation
from hi.apps.location.enums import LocationViewType
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewMode, ViewType
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEntityAddView(DualModeViewTestCase):
    """
    Tests for EntityAddView - demonstrates entity creation testing.
    This view handles adding new entities with automatic view integration.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str=str(LocationViewType.DEFAULT),
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )
        # Create test collection
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str=str(CollectionType.OTHER),
            collection_view_type_str=str(CollectionViewType.GRID)
        )

    def tearDown(self):
        """Clean up singletons when using real objects instead of mocks."""
        # Reset singleton managers to ensure clean state between tests
        try:
            CollectionManager._instance = None
        except ImportError:
            pass
        try:
            EntityManager._instance = None
        except ImportError:
            pass
        try:
            LocationManager._instance = None
        except ImportError:
            pass
        super().tearDown()

    def test_get_entity_add_form(self):
        """Test getting entity add form."""
        url = reverse('entity_edit_entity_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/entity_add.html')
        self.assertIn('entity_form', response.context)

    def test_get_entity_add_form_async(self):
        """Test getting entity add form with AJAX request."""
        url = reverse('entity_edit_entity_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        # Submit form with missing required fields
        form_data = {
            'name': '',  # Required field is empty
            # Missing entity_type_str (required)
        }

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Test that form errors are present in context
        self.assertIn('entity_form', response.context)
        form = response.context['entity_form']
        self.assertFalse(form.is_valid())
        
        # Should have validation errors for required fields
        self.assertTrue(form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('entity_type_str', form.errors)
        
        # Verify no Entity was created with invalid data
        self.assertFalse(Entity.objects.filter(name='').exists())

    def test_post_valid_form_location_view(self):
        """Test POST request with valid form data in location view context."""
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        # Create comprehensive form data for new entity
        form_data = {
            'name': 'Test Entity',
            'entity_type_str': str(EntityType.LIGHT)
        }

        # Count existing entities before
        initial_entity_count = Entity.objects.count()
        initial_position_count = EntityPosition.objects.count()

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, form_data)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        expected_url = reverse('home')
        self.assertEqual(data['location'], expected_url)
        
        # Test that new Entity was created
        self.assertEqual(Entity.objects.count(), initial_entity_count + 1)
        
        # Get the newly created entity
        new_entity = Entity.objects.get(name='Test Entity')
        self.assertEqual(new_entity.entity_type_str, str(EntityType.LIGHT))
        
        # Test that entity was added to the location view (EntityPosition created)
        # The real managers should handle this integration
        self.assertEqual(EntityPosition.objects.count(), initial_position_count + 1)
        
        # Verify the EntityPosition links the entity to the location
        entity_position = EntityPosition.objects.get(entity=new_entity)
        self.assertEqual(entity_position.location, self.location_view.location)

    def test_post_valid_form_collection_view(self):
        """Test POST request with valid form data in collection view context."""
        # Set collection view context
        self.setSessionViewType(ViewType.COLLECTION)
        
        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {
            'name': 'Test Entity Collection',
            'entity_type_str': str(EntityType.WALL_SWITCH)
        })

        # Expect antinode.js response (200 with JSON redirect)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Verify entity was actually created
        new_entity = Entity.objects.get(name='Test Entity Collection')
        self.assertEqual(new_entity.entity_type_str, str(EntityType.WALL_SWITCH))
        
        # Verify entity was added to a collection (test real behavior)
        # In collection view, entities should be added to the default collection
        # Check if any CollectionEntity relationship exists for this entity
        self.assertTrue(
            CollectionEntity.objects.filter(entity=new_entity).exists(),
            "Entity should be added to a collection in collection view"
        )

    def test_post_valid_form_other_view_type(self):
        """Test POST request with valid form data in other view type context."""
        # Set other view type context
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {
            'name': 'Test Entity Configuration',
            'entity_type_str': str(EntityType.MOTION_SENSOR)
        })

        # Expect antinode.js response (200 with JSON redirect)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Verify entity was actually created
        new_entity = Entity.objects.get(name='Test Entity Configuration')
        self.assertEqual(new_entity.entity_type_str, str(EntityType.MOTION_SENSOR))
        
        # Verify entity is NOT added to any collection in non-collection view type
        self.assertFalse(
            CollectionEntity.objects.filter(entity=new_entity).exists(),
            "Entity should NOT be added to any collection in configuration view"
        )

    def test_post_no_location_view_available(self):
        """Test POST request when no location view is available."""
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        # Delete all location views to create the no-location-view scenario
        LocationView.objects.all().delete()

        url = reverse('entity_edit_entity_add')
        response = self.client.post(url, {
            'name': 'Test Entity No Location',
            'entity_type_str': str(EntityType.PRESENCE_SENSOR)
        })

        # Expect antinode.js response (200 with JSON redirect)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Verify entity was still created even without location view
        new_entity = Entity.objects.get(name='Test Entity No Location')
        self.assertEqual(new_entity.entity_type_str, str(EntityType.PRESENCE_SENSOR))
        
        # Verify no EntityPosition was created since no location view exists
        self.assertFalse(
            EntityPosition.objects.filter(entity=new_entity).exists(),
            "No EntityPosition should be created when no location view available"
        )


class TestEntityDeleteView(DualModeViewTestCase):
    """
    Tests for EntityDeleteView - demonstrates entity deletion testing.
    This view handles entity deletion with permission checks.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test entity
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT)
        )

    def test_get_entity_delete_confirmation(self):
        """Test getting entity delete confirmation."""
        # Mock entity permission
        self.entity.can_user_delete = True

        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/entity_delete.html')
        self.assertEqual(response.context['entity'], self.entity)

    def test_get_entity_delete_async(self):
        """Test getting entity delete confirmation with AJAX request."""
        # Mock entity permission
        self.entity.can_user_delete = True

        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_get_entity_delete_permission_denied(self):
        """Test getting entity delete when not allowed."""
        # Mock entity permission
        self.entity.can_user_delete = False
        self.entity.save()

        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        
        response = self.client.get(url)
        self.assertEqual( response.status_code, 403)
        entity = Entity.objects.get(id=self.entity.id)
        self.assertIsNotNone( entity )

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_permission_denied(self):
        """Test POST request when deletion not allowed."""
        # Mock entity permission
        self.entity.can_user_delete = False
        self.entity.save()

        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {'action': 'confirm'})
        self.assertEqual(response.status_code, 403)
        entity = Entity.objects.get(id=self.entity.id)
        self.assertIsNotNone( entity )
        
    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        # Mock entity permission
        self.entity.can_user_delete = True
        self.entity.save()

        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Entity should be deleted
        with self.assertRaises(Entity.DoesNotExist):
            Entity.objects.get(id=self.entity.id)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_edit_entity_delete', kwargs={'entity_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestEntityPositionEditView(SyncViewTestCase):
    """
    Tests for EntityPositionEditView - demonstrates entity position editing testing.
    This view handles updating entity positions on location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test data
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT)
        )
        self.entity_position = EntityPosition.objects.create(
            entity=self.entity,
            location=self.location,
            svg_x=50.0,
            svg_y=50.0,
            svg_rotate=0.0,
            svg_scale=1.0
        )

    def test_post_valid_position_edit(self):
        """Test POST request with valid position data."""
        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            'svg_x': '60.0',
            'svg_y': '70.0',
            'svg_rotate': '0.0',
            'svg_scale': '1.0'
        })

        # Expect antinode.js response (200 with JSON)
        self.assertEqual(response.status_code, 200)
        
        # Verify the entity position was actually updated in the database
        updated_position = EntityPosition.objects.get(entity=self.entity)
        self.assertEqual(float(updated_position.svg_x), 60.0)
        self.assertEqual(float(updated_position.svg_y), 70.0)

    def test_post_invalid_position_edit(self):
        """Test POST request with invalid position data."""
        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            'svg_x': 'invalid',
            'svg_y': 'invalid',
            'svg_rotate': 'invalid',
            'svg_scale': 'invalid'
        })

        # Should still return success response (antinode.js pattern)
        # The view likely handles form validation gracefully
        self.assertEqual(response.status_code, 200)
        
        # Verify the entity position was NOT updated (should remain original values)
        unchanged_position = EntityPosition.objects.get(entity=self.entity)
        self.assertEqual(float(unchanged_position.svg_x), 50.0)  # Original value
        self.assertEqual(float(unchanged_position.svg_y), 50.0)  # Original value

    def test_post_nonexistent_position(self):
        """Test POST request for nonexistent entity position."""
        # Create entity without position
        other_entity = Entity.objects.create(
            name='Other Entity',
            entity_type_str=str(EntityType.ON_OFF_SWITCH)
        )

        url = reverse('entity_position_edit', kwargs={'entity_id': other_entity.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_position_edit', kwargs={'entity_id': 99999})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('entity_position_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestManagePairingsView(DualModeViewTestCase):
    """
    Tests for ManagePairingsView - demonstrates entity pairing management testing.
    This view handles managing entity pairings.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test entities
        self.entity = Entity.objects.create(
            name='Primary Entity',
            entity_type_str=str(EntityType.THERMOSTAT)
        )
        self.paired_entity1 = Entity.objects.create(
            name='Paired Entity 1',
            entity_type_str=str(EntityType.THERMOMETER)
        )
        self.paired_entity2 = Entity.objects.create(
            name='Paired Entity 2',
            entity_type_str=str(EntityType.HYGROMETER)
        )
        self.candidate_entity = Entity.objects.create(
            name='Candidate Entity',
            entity_type_str=str(EntityType.BAROMETER)
        )
    
    def tearDown(self):
        """Clean up singletons when using real objects instead of mocks."""
        # Reset singleton managers to ensure clean state between tests
        try:
            EntityPairingManager._instance = None
        except Exception:
            pass
        try:
            EntityManager._instance = None
        except Exception:
            pass
        super().tearDown()

    def test_get_manage_pairings(self):
        """Test getting manage pairings view."""
        # Create actual entity pairings in the database
        # EntityPairingManager looks for entities with delegate relationships
        # We'll set up the entities to have the proper relationships
        
        # Create entity states to establish principal/delegate relationships
        from hi.apps.entity.models import EntityState
        from hi.apps.entity.enums import EntityStateType
        
        # Give the primary entity some states so it can be a principal
        EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str=str(EntityStateType.TEMPERATURE),
            name='temperature'
        )
        
        # Set up delegate relationships using EntityStateDelegation
        from hi.apps.entity.models import EntityStateDelegation
        
        # Create delegations from the primary entity to paired entities
        for entity_state in self.entity.states.all():
            EntityStateDelegation.objects.create(
                entity_state=entity_state,
                delegate_entity=self.paired_entity1
            )
            EntityStateDelegation.objects.create(
                entity_state=entity_state,
                delegate_entity=self.paired_entity2
            )
        
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'entity/edit/modals/manage_pairings.html')
        
        self.assertEqual(response.context['entity'], self.entity)
        self.assertIn('entity_view_group_list', response.context)
        self.assertEqual(response.context['principal_entity_id_name_prefix'],
                         ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX)
        
        # Verify the view groups were created (should be a list)
        entity_view_groups = response.context['entity_view_group_list']
        self.assertIsNotNone(entity_view_groups)
        self.assertIsInstance(entity_view_groups, list)

    def test_get_manage_pairings_async(self):
        """Test getting manage pairings view with AJAX request."""
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_update_pairings_success(self):
        """Test POST request to update entity pairings successfully."""
        # Set up initial pairings
        from hi.apps.entity.models import EntityState
        from hi.apps.entity.enums import EntityStateType
        
        # Give the primary entity some states so it can be a principal
        EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str=str(EntityStateType.TEMPERATURE),
            name='temperature'
        )
        
        # Initially pair entity1 with the primary entity using EntityStateDelegation
        from hi.apps.entity.models import EntityStateDelegation
        for entity_state in self.entity.states.all():
            EntityStateDelegation.objects.create(
                entity_state=entity_state,
                delegate_entity=self.paired_entity1
            )
        
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity1.id}': 'on',
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.candidate_entity.id}': 'on',
            'other-field': 'ignored'
        })

        # Should return success (200 with JSON for antinode.js)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify the pairings were updated in the database
        # Check that delegations exist for both entities
        paired_entity1_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.paired_entity1,
            entity_state__entity=self.entity
        ).count()
        
        candidate_entity_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.candidate_entity,
            entity_state__entity=self.entity
        ).count()
        
        # Both should have delegation relationships
        self.assertGreater(paired_entity1_delegations, 0)
        self.assertGreater(candidate_entity_delegations, 0)

    def test_post_update_pairings_error(self):
        """Test POST request to update entity pairings with error."""
        # Try to create an invalid pairing scenario
        # For example, trying to pair an entity with itself or with invalid entities
        
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        
        # Try to pair with a non-existent entity ID
        response = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}99999': 'on'
        })

        # Should handle the error gracefully
        # The view should still return success but the pairing won't be created
        self.assertSuccessResponse(response)

    def test_post_update_pairings_empty_selection(self):
        """Test POST request with no paired entities selected."""
        # Set up initial pairings
        from hi.apps.entity.models import EntityState
        from hi.apps.entity.enums import EntityStateType
        
        # Give the primary entity some states
        EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str=str(EntityStateType.TEMPERATURE),
            name='temperature'
        )
        
        # Initially pair entities with the primary entity using EntityStateDelegation
        from hi.apps.entity.models import EntityStateDelegation
        for entity_state in self.entity.states.all():
            EntityStateDelegation.objects.create(
                entity_state=entity_state,
                delegate_entity=self.paired_entity1
            )
            EntityStateDelegation.objects.create(
                entity_state=entity_state,
                delegate_entity=self.paired_entity2
            )
        
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            'other-field': 'value'
            # No entity pairing fields selected
        })

        # Should succeed
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify all pairings were removed (empty selection means unpair all)
        # Check that no delegations exist for these entities
        paired_entity1_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.paired_entity1,
            entity_state__entity=self.entity
        ).count()
        
        paired_entity2_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.paired_entity2,
            entity_state__entity=self.entity
        ).count()
        
        # Both should have no delegation relationships
        self.assertEqual(paired_entity1_delegations, 0)
        self.assertEqual(paired_entity2_delegations, 0)

    def test_post_update_pairings_field_parsing(self):
        """Test POST request field parsing for entity IDs."""
        # Set up the entity to be able to have pairings
        from hi.apps.entity.models import EntityState
        from hi.apps.entity.enums import EntityStateType
        
        EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str=str(EntityStateType.TEMPERATURE),
            name='temperature'
        )
        
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, {
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity1.id}': 'on',
            f'{ManagePairingsView.ENTITY_PAIR_ID_NAME_PREFIX}{self.paired_entity2.id}': 'on',
            'entity-pair-id-invalid': 'on',  # Should be ignored (no number)
            'wrong-prefix-123': 'on',  # Should be ignored (wrong prefix)
            'no-numbers-here': 'on'  # Should be ignored (no match)
        })

        # Should succeed
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify only the valid entity IDs were processed
        # Check delegation relationships
        paired_entity1_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.paired_entity1,
            entity_state__entity=self.entity
        ).count()
        
        paired_entity2_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.paired_entity2,
            entity_state__entity=self.entity
        ).count()
        
        candidate_entity_delegations = EntityStateDelegation.objects.filter(
            delegate_entity=self.candidate_entity,
            entity_state__entity=self.entity
        ).count()
        
        # Only entity1 and entity2 should be paired
        self.assertGreater(paired_entity1_delegations, 0)
        self.assertGreater(paired_entity2_delegations, 0)
        # Candidate entity should not be paired (wasn't in the request)
        self.assertEqual(candidate_entity_delegations, 0)

    def test_nonexistent_entity_returns_404(self):
        """Test that accessing nonexistent entity returns 404."""
        url = reverse('entity_edit_manage_pairings', kwargs={'entity_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
