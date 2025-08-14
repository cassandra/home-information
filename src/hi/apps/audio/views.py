import logging

from hi.hi_async_view import HiModalView

logger = logging.getLogger(__name__)


class AudioPermissionGuidanceView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'audio/modals/audio_permission_guidance.html'
