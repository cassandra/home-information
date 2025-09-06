from hi.hi_async_view import HiModalView

from .zm_sync import ZoneMinderSynchronizer


class ZmSyncView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'common/modals/processing_result.html'

    def post(self, request, *args, **kwargs):

        processing_result = ZoneMinderSynchronizer().sync()
        context = {
            'processing_result': processing_result,
        }
        return self.modal_response( request, context )
