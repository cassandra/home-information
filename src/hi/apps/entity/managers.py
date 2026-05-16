from django.db.models import Q

from hi.integrations.managers import IntegrationDetailsManager


class EntityManager( IntegrationDetailsManager ):
    """Adds capability-shaped queryset helpers used by callers that
    filter entities by what they can present visually.

    ``with_live_view`` is broad: any current visual exists (native
    stream, streamable snapshot, or static snapshot). ``with_live_feed``
    is narrow: a *moving* visual is available (native stream or a
    snapshot polled fast enough). See the matching derived properties
    on Entity."""

    def with_live_view( self ):
        return self.filter(
            Q( has_video_stream = True ) | Q( has_video_snapshot = True )
        )

    def with_live_feed( self ):
        return self.filter(
            Q( has_video_stream = True )
            | (
                Q( has_video_snapshot = True )
                & Q( video_snapshot_stream_fps__gt = 0 )
            )
        )
