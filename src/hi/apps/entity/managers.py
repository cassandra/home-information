from django.db.models import Q

from hi.integrations.managers import IntegrationDetailsModelManager


class EntityModelManager( IntegrationDetailsModelManager ):

    def with_live_view( self ):
        """Entities that have *any* current visual — native stream or
        snapshot. Mirrors the ``has_live_view`` property in queryset
        form for filter sites."""
        return self.filter(
            Q( has_video_stream = True ) | Q( has_video_snapshot = True )
        )
