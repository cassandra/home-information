import logging
from typing import Dict, Optional

from django.core.files.storage import default_storage
from django.db import models

from hi.apps.attribute.models import AttributeModel, AttributeValueHistoryModel

from .transient_models import IntegrationKey, IntegrationDetails
from .managers import (
    EntityExternalReferenceManager,
    IntegrationDetailsModelManager,
    LocationExternalReferenceManager,
)


logger = logging.getLogger(__name__)


class Integration( models.Model ):

    integration_id = models.CharField(
        'Integration Id',
        max_length = 64,
        null = False, blank = False,
        unique = True,
    )
    is_enabled = models.BooleanField(
        'Enabled?',
        default = False,
    )
    is_paused = models.BooleanField(
        'Paused?',
        default = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'

    def __str__(self):
        return self.integration_id
   
    @property
    def attributes_by_name(self) -> Dict[ str, 'IntegrationAttribute' ]:
        return { attr.name: attr for attr in self.attributes.all() }

    @property
    def attributes_by_integration_key(self) -> Dict[ IntegrationKey, 'IntegrationAttribute' ]:
        return { attr.integration_key: attr for attr in self.attributes.all() }
    

class IntegrationAttribute( AttributeModel ):

    integration = models.ForeignKey(
        Integration,
        related_name = 'attributes',
        verbose_name = 'Integration',
        on_delete = models.CASCADE,
    )
    description = models.TextField(
        'Description',
        blank = True,
        default = '',
    )

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'
        ordering = ['order_id', 'id']

    @property
    def display_description( self ):
        return self.description or ''

    def get_upload_to(self):
        return 'integration/attributes/'

    def _get_history_model_class(self):
        return IntegrationAttributeHistory


class IntegrationDetailsModel( models.Model ):
    """Mixin for DB models that need integration provenance fields
    (active key, previous-disconnected key, and arbitrary payload)."""
    objects = IntegrationDetailsModelManager()
    
    class Meta:
        abstract = True

    integration_id = models.CharField(
        'Integration Id',
        max_length = 32,
        null = True, blank = True,
    )
    integration_name = models.CharField(
        'Integration Name',
        max_length = 128,
        null = True, blank = True,
    )
    integration_payload = models.JSONField(
        'Integration Payload',
        default = dict,
        blank = True,
        help_text = 'Integration-specific data (e.g., HA domain, device capabilities)',
    )
    # The previous_integration_* fields record the integration identity an
    # instance had at the moment it was disconnected. They drive the
    # auto-reconnect path: when an upstream entity reappears whose key
    # matches a disconnected entity's previous identity, the entity is
    # reconnected rather than a duplicate being created. The
    # previous_integration_id is indexed because the secondary-match query
    # during sync filters on it.
    previous_integration_id = models.CharField(
        'Previous Integration Id',
        max_length = 32,
        null = True, blank = True,
        db_index = True,
    )
    previous_integration_name = models.CharField(
        'Previous Integration Name',
        max_length = 128,
        null = True, blank = True,
    )

    @property
    def integration_key(self) -> IntegrationKey:
        # Returns None when the underlying fields are unset, so reading on a
        # never-attached or already-disconnected instance is safe. Round-trips
        # through the setter as a no-op clear.
        if self.integration_id is None or self.integration_name is None:
            return None
        return IntegrationKey(
            integration_id = self.integration_id,
            integration_name = self.integration_name,
        )

    @integration_key.setter
    def integration_key( self, integration_key : IntegrationKey ):
        if not integration_key:
            self.integration_id = None
            self.integration_name = None
            return
        self.integration_id = integration_key.integration_id
        self.integration_name = integration_key.integration_name
        # Re-attaching to an active integration invalidates any prior
        # detached-state record. Clearing here is defensive: a stale
        # previous_integration_* pair on an active entity would confuse
        # queries that filter disconnected entities on previous_integration_id.
        self.previous_integration_id = None
        self.previous_integration_name = None
        return

    @property
    def previous_integration_key(self) -> IntegrationKey:
        if self.previous_integration_id is None or self.previous_integration_name is None:
            return None
        return IntegrationKey(
            integration_id = self.previous_integration_id,
            integration_name = self.previous_integration_name,
        )

    @previous_integration_key.setter
    def previous_integration_key( self, integration_key : IntegrationKey ):
        if not integration_key:
            self.previous_integration_id = None
            self.previous_integration_name = None
            return
        self.previous_integration_id = integration_key.integration_id
        self.previous_integration_name = integration_key.integration_name
        return

    def get_integration_details(self) -> IntegrationDetails:
        return IntegrationDetails(
            key = self.integration_key,
            payload = self.integration_payload,
        )

    def update_integration_payload(self, new_payload: dict) -> list:
        """
        Update integration payload and return list of changed fields.
        Reports modifications to existing fields by name; returns an
        empty list when nothing changed (no DB write performed).
        """
        old_payload = self.integration_payload or {}
        if old_payload == new_payload:
            return []

        changed_fields = []
        for key, new_value in new_payload.items():
            if key in old_payload and old_payload[key] != new_value:
                changed_fields.append(f'{key}: {old_payload[key]} -> {new_value}')

        self.integration_payload = new_payload
        self.save()

        return changed_fields


class IntegrationAttributeHistory(AttributeValueHistoryModel):

    attribute = models.ForeignKey(
        IntegrationAttribute,
        related_name='history',
        verbose_name='Integration Attribute',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Integration Attribute History'
        verbose_name_plural = 'Integration Attribute History'
        indexes = [
            models.Index(fields=['attribute', '-changed_datetime']),
        ]


def _external_reference_upload_to( instance, filename ):
    """Per-owner-type, per-integration thumbnail path. Concrete
    subclasses set ``_owner_type_path_segment`` so this resolves
    without per-subclass duplication."""
    return (
        f'{instance._owner_type_path_segment}/external/'
        f'{instance.integration_id}/thumbnails/{filename}'
    )


class ExternalReferenceBase( models.Model ):
    """Abstract base for the per-owner external-reference tables.

    Each row represents an upstream item (Paperless document, Immich
    asset, etc.) attached to an HI Entity or Location. Field naming
    follows IntegrationKey -- ``(integration_id, integration_name)``
    -- so the existing IntegrationKey machinery rounds-trips through
    the property/setter below. ``integration_name`` holds the
    upstream's opaque identifier (Immich UUID, Paperless document
    id, etc.).

    Thumbnail bytes are persisted under MEDIA_ROOT; ``delete()``
    cleans up the file on a best-effort basis.
    """

    integration_id = models.CharField(
        'Integration Id',
        max_length = 32,
        db_index = True,
    )
    integration_name = models.CharField(
        'Integration Name',
        max_length = 255,
    )
    title = models.CharField(
        'Title',
        max_length = 255,
    )
    source_url = models.URLField(
        'Source URL',
        max_length = 2048,
    )
    mime_type = models.CharField(
        'MIME Type',
        max_length = 128,
        blank = True,
        default = '',
    )
    thumbnail = models.FileField(
        'Thumbnail',
        upload_to = _external_reference_upload_to,
        blank = True,
        null = True,
    )
    order_id = models.PositiveIntegerField(
        'Order',
        default = 0,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
        blank = True,
    )

    # Concrete subclasses set this to the path segment used in
    # ``_external_reference_upload_to``: ``'entity'`` or ``'location'``.
    _owner_type_path_segment: str = ''

    class Meta:
        abstract = True
        ordering = [ 'order_id', '-created_datetime' ]

    @property
    def integration_key(self) -> Optional[IntegrationKey]:
        # Returns None when fields are unset (shouldn't happen on a
        # saved row; defensive).
        if self.integration_id is None or self.integration_name is None:
            return None
        return IntegrationKey(
            integration_id = self.integration_id,
            integration_name = self.integration_name,
        )

    @integration_key.setter
    def integration_key(self, integration_key: Optional[IntegrationKey]):
        if not integration_key:
            self.integration_id = None
            self.integration_name = None
            return
        self.integration_id = integration_key.integration_id
        self.integration_name = integration_key.integration_name

    def delete(self, *args, **kwargs):
        """Best-effort thumbnail file cleanup."""
        thumbnail_name = self.thumbnail.name if self.thumbnail else None
        if thumbnail_name:
            try:
                if default_storage.exists( thumbnail_name ):
                    default_storage.delete( thumbnail_name )
                    logger.debug(
                        f'Deleted external-reference thumbnail: {thumbnail_name}'
                    )
            except Exception as e:
                logger.warning(
                    f'Error deleting external-reference thumbnail '
                    f'{thumbnail_name}: {e}'
                )
        return super().delete( *args, **kwargs )


class EntityExternalReference( ExternalReferenceBase ):

    entity = models.ForeignKey(
        'entity.Entity',
        related_name = 'external_references',
        verbose_name = 'Entity',
        on_delete    = models.CASCADE,
    )

    _owner_type_path_segment = 'entity'

    objects = EntityExternalReferenceManager()

    class Meta( ExternalReferenceBase.Meta ):
        verbose_name = 'Entity External Reference'
        verbose_name_plural = 'Entity External References'
        unique_together = [ ( 'entity', 'integration_id', 'integration_name' ) ]


class LocationExternalReference( ExternalReferenceBase ):

    location = models.ForeignKey(
        'location.Location',
        related_name = 'external_references',
        verbose_name = 'Location',
        on_delete    = models.CASCADE,
    )

    _owner_type_path_segment = 'location'

    objects = LocationExternalReferenceManager()

    class Meta( ExternalReferenceBase.Meta ):
        verbose_name = 'Location External Reference'
        verbose_name_plural = 'Location External References'
        unique_together = [ ( 'location', 'integration_id', 'integration_name' ) ]
