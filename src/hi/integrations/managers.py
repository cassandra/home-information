import logging
from typing import Optional, Sequence

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Q

from .transient_models import IntegrationKey


logger = logging.getLogger(__name__)


class IntegrationDetailsModelManager(models.Manager):

    def filter_by_integration_key( self, integration_key : IntegrationKey ):
        return self.filter( integration_id = integration_key.integration_id,
                            integration_name = integration_key.integration_name )

    def filter_by_integration_keys( self, integration_keys : Sequence[ IntegrationKey ] ):
        if not integration_keys:
            return self.none()

        query = Q()
        for integration_key in integration_keys:
            query |= Q( integration_id = integration_key.integration_id,
                        integration_name = integration_key.integration_name )
            continue
        return self.filter(query)


class ExternalReferenceManagerBase( models.Manager ):
    """Shared upsert logic for the two ExternalReference concrete
    models. Concrete managers set ``_owner_field_name`` to wire the
    owner FK into the lookup."""

    _owner_field_name: str = ''

    def create_or_update(
            self, *,
            owner,
            integration_key  : IntegrationKey,
            title            : str,
            source_url       : str,
            mime_type        : str             = '',
            thumbnail_bytes  : Optional[bytes] = None,
    ):
        """Upsert by ``(owner, integration_key)``.

        On insert all fields are set; the thumbnail file is written
        when ``thumbnail_bytes`` is provided. On update,
        ``source_url`` and ``mime_type`` are overwritten with the
        upstream's current values; ``title``, ``order_id``, and
        ``created_datetime`` are preserved (operator may have edited
        the title locally and the position is the operator's, not
        the upstream's); ``updated_datetime`` bumps; the thumbnail
        is re-written when ``thumbnail_bytes`` is provided (None
        leaves the existing thumbnail intact so a transient upstream
        thumbnail outage doesn't blank out an otherwise-good card).
        """
        lookup = {
            self._owner_field_name : owner,
            'integration_id'       : integration_key.integration_id,
            'integration_name'     : integration_key.integration_name,
        }
        existing = self.filter( **lookup ).first()

        if existing is None:
            # Insert path is two saves separated by a file write
            # (FileField.save() doesn't bind the new path until we
            # save the model row again). Wrap in atomic so the row
            # state is consistent even if the second save fails;
            # the file itself isn't rolled back by atomic, but
            # orphan media files are the existing best-effort
            # tradeoff (see AttributeModel.delete()).
            with transaction.atomic():
                instance = self.model(
                    **lookup,
                    title      = title,
                    source_url = source_url,
                    mime_type  = mime_type or '',
                )
                instance.save()
                if thumbnail_bytes:
                    self._write_thumbnail(
                        instance, integration_key.integration_name, thumbnail_bytes,
                    )
                    instance.save( update_fields = [ 'thumbnail', 'updated_datetime' ] )
            return instance

        existing.source_url = source_url
        existing.mime_type = mime_type or ''
        update_fields = [ 'source_url', 'mime_type', 'updated_datetime' ]
        if thumbnail_bytes:
            self._write_thumbnail(
                existing, integration_key.integration_name, thumbnail_bytes,
            )
            update_fields.append( 'thumbnail' )
        existing.save( update_fields = update_fields )
        return existing

    @staticmethod
    def _write_thumbnail(
            instance, integration_name : str, thumbnail_bytes : bytes,
    ):
        # Stable, filesystem-safe filename per integration_name so
        # repeated upsert calls land on the same path. Deleting any
        # pre-existing file first sidesteps Django FileField's
        # uniqueness-suffix collision handling.
        safe_name = integration_name.replace( '/', '_' ).replace( '\\', '_' )
        filename = f'{safe_name}.png'
        if instance.thumbnail:
            try:
                instance.thumbnail.delete( save = False )
            except Exception as e:
                logger.warning(
                    f'Error deleting old external-reference thumbnail '
                    f'{instance.thumbnail.name}: {e}'
                )
        instance.thumbnail.save(
            filename, ContentFile( thumbnail_bytes ), save = False,
        )


class EntityExternalReferenceManager( ExternalReferenceManagerBase ):
    _owner_field_name = 'entity'


class LocationExternalReferenceManager( ExternalReferenceManagerBase ):
    _owner_field_name = 'location'
    
