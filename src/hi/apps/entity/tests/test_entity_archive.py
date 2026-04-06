import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import (
    ArchivedEntity,
    ArchivedEntityAttribute,
    Entity,
    EntityAttribute,
)
from hi.enums import ViewMode
from hi.testing.view_test_base import SyncViewTestCase

from .synthetic_data import EntityAttributeSyntheticData

logging.disable( logging.CRITICAL )


class TestEntityArchiveOperation( SyncViewTestCase ):

    def setUp( self ):
        super().setUp()
        self.setSessionViewMode( ViewMode.EDIT )
        return

    def _create_archivable_entity( self, **kwargs ):
        defaults = { 'integration_id': None, 'integration_name': None }
        defaults.update( kwargs )
        return EntityAttributeSyntheticData.create_test_entity( **defaults )

    def test_archive_copies_entity_identity_and_deletes_original( self ):
        entity = self._create_archivable_entity( name = 'Pool Pump' )
        entity_id = entity.id
        original_created = entity.created_datetime

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity_id } )
        self.client.post( url, { 'action': 'confirm' } )

        self.assertFalse( Entity.objects.filter( pk = entity_id ).exists() )

        archived = ArchivedEntity.objects.get()
        self.assertEqual( archived.name, 'Pool Pump' )
        self.assertEqual( archived.entity_type_str, entity.entity_type_str )
        self.assertEqual( archived.original_created_datetime, original_created )
        self.assertIsNotNone( archived.archived_datetime )
        return

    def test_archive_copies_text_attributes( self ):
        entity = self._create_archivable_entity()
        EntityAttribute.objects.create(
            entity = entity,
            name = 'Serial Number',
            value = 'SN-12345',
            attribute_type_str = str( AttributeType.CUSTOM ),
            value_type_str = str( AttributeValueType.TEXT ),
            order_id = 0,
        )
        EntityAttribute.objects.create(
            entity = entity,
            name = 'Model',
            value = 'XP-500',
            attribute_type_str = str( AttributeType.PREDEFINED ),
            value_type_str = str( AttributeValueType.TEXT ),
            order_id = 1,
        )

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity.id } )
        self.client.post( url, { 'action': 'confirm' } )

        archived = ArchivedEntity.objects.get()
        archived_attrs = list( archived.attributes.order_by( 'order_id' ) )
        self.assertEqual( len( archived_attrs ), 2 )

        self.assertEqual( archived_attrs[0].name, 'Serial Number' )
        self.assertEqual( archived_attrs[0].value, 'SN-12345' )
        self.assertEqual( archived_attrs[0].attribute_type_str, str( AttributeType.CUSTOM ) )
        self.assertEqual( archived_attrs[0].order_id, 0 )

        self.assertEqual( archived_attrs[1].name, 'Model' )
        self.assertEqual( archived_attrs[1].value, 'XP-500' )
        self.assertEqual( archived_attrs[1].attribute_type_str, str( AttributeType.PREDEFINED ) )
        self.assertEqual( archived_attrs[1].order_id, 1 )
        return

    def test_archive_file_attribute_preserves_file_reference( self ):
        entity = self._create_archivable_entity()
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute( entity = entity )
        original_file_name = file_attr.file_value.name

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity.id } )
        self.client.post( url, { 'action': 'confirm' } )

        archived = ArchivedEntity.objects.get()
        archived_attr = archived.attributes.get()
        self.assertEqual( archived_attr.file_value.name, original_file_name )
        return

    def test_archive_integration_entity_blocked( self ):
        entity = EntityAttributeSyntheticData.create_test_entity()
        self.assertIsNotNone( entity.integration_id )
        entity_id = entity.id

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity_id } )
        response = self.client.post( url, { 'action': 'confirm' } )

        self.assertEqual( response.status_code, 403 )
        self.assertTrue( Entity.objects.filter( pk = entity_id ).exists() )
        self.assertFalse( ArchivedEntity.objects.exists() )
        return

    def test_archive_without_confirm_rejected( self ):
        entity = self._create_archivable_entity()
        entity_id = entity.id

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity_id } )
        response = self.client.post( url, { 'action': 'wrong' } )

        self.assertEqual( response.status_code, 400 )
        self.assertTrue( Entity.objects.filter( pk = entity_id ).exists() )
        self.assertFalse( ArchivedEntity.objects.exists() )
        return

    def test_archive_entity_with_no_attributes( self ):
        entity = self._create_archivable_entity( name = 'Empty Entity' )

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity.id } )
        self.client.post( url, { 'action': 'confirm' } )

        archived = ArchivedEntity.objects.get()
        self.assertEqual( archived.name, 'Empty Entity' )
        self.assertEqual( archived.attributes.count(), 0 )
        return


class TestEntityArchiveIntegrationGuard( SyncViewTestCase ):

    def setUp( self ):
        super().setUp()
        self.setSessionViewMode( ViewMode.EDIT )
        return

    def test_archive_get_integration_entity_returns_403( self ):
        entity = EntityAttributeSyntheticData.create_test_entity()
        self.assertIsNotNone( entity.integration_id )

        url = reverse( 'entity_edit_entity_archive', kwargs = { 'entity_id': entity.id } )
        response = self.client.get( url )

        self.assertEqual( response.status_code, 403 )
        return


class TestEntityArchiveListView( SyncViewTestCase ):

    def test_archive_list_returns_archived_entities( self ):
        ArchivedEntity.objects.create(
            name = 'Old Pump',
            entity_type_str = 'other',
        )
        ArchivedEntity.objects.create(
            name = 'Old Heater',
            entity_type_str = 'other',
        )

        url = reverse( 'entity_edit_archive_list' )
        response = self.client.get( url )

        self.assertSuccessResponse( response )
        archived = response.context['archived_entities']
        self.assertEqual( archived.count(), 2 )
        return


class TestEntityArchiveDetailView( SyncViewTestCase ):

    def test_archive_detail_returns_entity_and_attributes( self ):
        archived_entity = ArchivedEntity.objects.create(
            name = 'Old Pump',
            entity_type_str = 'other',
        )
        ArchivedEntityAttribute.objects.create(
            archived_entity = archived_entity,
            name = 'Serial',
            value = 'SN-999',
            attribute_type_str = str( AttributeType.CUSTOM ),
            value_type_str = str( AttributeValueType.TEXT ),
        )
        ArchivedEntityAttribute.objects.create(
            archived_entity = archived_entity,
            name = 'Manual',
            value = 'manual.pdf',
            attribute_type_str = str( AttributeType.CUSTOM ),
            value_type_str = str( AttributeValueType.FILE ),
        )

        url = reverse( 'entity_edit_archive_detail',
                       kwargs = { 'archived_entity_id': archived_entity.id } )
        response = self.client.get( url )

        self.assertSuccessResponse( response )
        self.assertEqual( response.context['archived_entity'], archived_entity )
        self.assertEqual( response.context['attributes'].count(), 2 )
        return

    def test_archive_detail_nonexistent_returns_404( self ):
        url = reverse( 'entity_edit_archive_detail',
                       kwargs = { 'archived_entity_id': 99999 } )
        response = self.client.get( url )

        self.assertEqual( response.status_code, 404 )
        return
