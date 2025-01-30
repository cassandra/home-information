from django.core.exceptions import BadRequest
from django.http import Http404
from django.views.generic import View

from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.sense.models import Sensor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin

from hi.enums import ViewType
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView

from .constants import ConsoleConstants
from .settings import ConsoleSetting


class SensorVideoStreamView( HiGridView, SensorResponseMixin ):

    def get_main_template_name( self ) -> str:
        return 'console/panes/sensor_video_stream.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        sensor_id = kwargs.get('sensor_id')
        try:
            sensor = Sensor.objects.get( id = sensor_id )
        except Sensor.DoesNotExist:
            raise Http404('Sensor not found.')

        sensor_response_map = self.sensor_response_manager().get_latest_sensor_responses(
            sensor_list = [ sensor ],
        )
        if not sensor_response_map or not sensor_response_map[sensor]:
            raise BadRequest( 'Video stream is not currently available.' )

        request.view_parameters.view_type = ViewType.VIDEO_STREAM
        request.view_parameters.to_session( request )
        return {
            'sensor': sensor,
            'sensor_response': sensor_response_map[sensor][0],
        }

        
class ConsoleLockView( View, SettingsMixin ):

    def post( self, request, *args, **kwargs ):
        lock_password = self.settings_manager().get_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD )
        if not lock_password:
            return SetLockPasswordView().get( request, *args, **kwargs )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class SetLockPasswordView( HiModalView, SettingsMixin ):

    def get_template_name( self ) -> str:
        return 'console/modals/set_lock_password.html'
    
    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
    def post( self, request, *args, **kwargs ):
        input_password = request.POST.get('password')
        if not input_password:
            raise BadRequest( 'No password provided.' )
        self.settings_manager().set_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD, input_password )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class ConsoleUnlockView( HiModalView, SettingsMixin ):

    def get_template_name( self ) -> str:
        return 'console/modals/console_unlock.html'

    def get(self, request, *args, **kwargs):
        return self.modal_response( request )
                                    
    def post(self, request, *args, **kwargs):

        # N.B. Simplified security of console locking for now. Just meant
        # to be used when visitors in the house to prevent snooping. Beef
        # up security here if/when needed, but eventual login requirements
        # and its session will be the main auth method.
        
        input_password = request.POST.get('password')
        if not input_password:
            raise BadRequest( 'No password provided.' )

        lock_password = self.settings_manager().get_setting_value( ConsoleSetting.CONSOLE_LOCK_PASSWORD )

        if lock_password and ( input_password != lock_password ):
            raise BadRequest( 'Invalid password.' )
                               
        # N.B. It should not be possible to get into state where console is
        # locked without a password set.  However, if it happens, it would
        # be impossible to unlock the console. Thus, we'll unlock in that
        # exceptional case.

        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = False
        return self.refresh_response( request= request )

    
