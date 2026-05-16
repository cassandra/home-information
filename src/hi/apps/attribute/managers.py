from django.db import models


class ActiveAttributeModelManager( models.Manager ):
    """Default manager that hides soft-deleted attributes."""

    def get_queryset( self ):
        return super().get_queryset().filter( is_deleted = False )


class DeletedAttributeModelManager( models.Manager ):
    """Manager that returns only soft-deleted attributes."""

    def get_queryset( self ):
        return super().get_queryset().filter( is_deleted = True )
