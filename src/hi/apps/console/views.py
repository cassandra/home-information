from datetime import datetime, timedelta
from django.core.exceptions import BadRequest
from django.http import Http404
from django.views.generic import View

from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityStateType
from hi.apps.sense.models import Sensor
from hi.integrations.integration_manager import IntegrationManager

from hi.enums import ViewType
from hi.hi_async_view import HiModalView
from hi.hi_grid_view import HiGridView

from .constants import ConsoleConstants
from .console_helper import ConsoleSettingsHelper


class EntityVideoStreamView( HiGridView ):
    """View for displaying entity-based video streams."""

    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_pane.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        entity_id = kwargs.get('entity_id')
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404('Entity not found.')

        # Check if entity has video stream capability
        if not entity.has_video_stream:
            raise BadRequest( 'Entity does not have video stream capability.' )

        # Get the integration gateway for this entity
        integration_gateway = IntegrationManager().get_integration_gateway( entity.integration_id )
        if not integration_gateway:
            raise BadRequest( 'Integration not available for video stream.' )

        # Get the video stream using the integration gateway
        if not entity.has_video_stream:
            raise BadRequest( 'Video stream is not currently available.' )

        # Find the first sensor with video capability for history browsing
        # Using priority order to select the best sensor
        video_sensor = None
        for state_type in EntityVideoSensorHistoryView.SENSOR_STATE_TYPE_PRIORITY:
            for state in entity.states.filter(entity_state_type_str=str(state_type)):
                sensor = state.sensors.filter(provides_video_stream=True).first()
                if sensor:
                    video_sensor = sensor
                    break
            if video_sensor:
                break
        
        # If no prioritized sensor found, just get any video-capable sensor
        if not video_sensor:
            for state in entity.states.all():
                sensor = state.sensors.filter(provides_video_stream=True).first()
                if sensor:
                    video_sensor = sensor
                    break
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        return {
            'entity': entity,
            'video_sensor': video_sensor,  # May be None if no video sensors
        }


class EntityVideoSensorHistoryView( HiGridView ):
    """View for browsing sensor history records with video streams."""
    
    # Priority order for selecting default sensor with video capability
    SENSOR_STATE_TYPE_PRIORITY = [
        EntityStateType.MOVEMENT,
        EntityStateType.PRESENCE,
        EntityStateType.OPEN_CLOSE,
        EntityStateType.ON_OFF,
    ]
    
    def get_main_template_name( self ) -> str:
        return 'console/panes/entity_video_sensor_history.html'
    
    def get_main_template_context( self, request, *args, **kwargs ):
        entity_id = kwargs.get('entity_id')
        sensor_id = kwargs.get('sensor_id')
        sensor_history_id = kwargs.get('sensor_history_id')
        
        # Get the entity
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404('Entity not found.')
        
        # Check if entity has video stream capability
        if not entity.has_video_stream:
            raise BadRequest( 'Entity does not have video stream capability.' )
        
        # Get the sensor
        try:
            sensor = Sensor.objects.get( id = sensor_id, entity_state__entity = entity )
        except Sensor.DoesNotExist:
            raise Http404('Sensor not found for this entity.')
        
        # For Phase 1: Create mock sensor history data
        mock_history_items = self._create_mock_sensor_history( sensor, sensor_history_id )
        
        # Determine the current sensor history item to display
        if sensor_history_id:
            current_history = next((h for h in mock_history_items if h['id'] == int(sensor_history_id)), None)
            if not current_history:
                current_history = mock_history_items[0] if mock_history_items else None
        else:
            # Default to most recent
            current_history = mock_history_items[0] if mock_history_items else None
        
        # Group history items by time period (hourly if >10 in a day, otherwise daily)
        timeline_groups = self._group_history_by_time( mock_history_items )
        
        # Find previous and next items for navigation
        prev_history = None
        next_history = None
        if current_history:
            current_idx = mock_history_items.index(current_history)
            if current_idx > 0:
                prev_history = mock_history_items[current_idx - 1]
            if current_idx < len(mock_history_items) - 1:
                next_history = mock_history_items[current_idx + 1]
        
        request.view_parameters.view_type = ViewType.ENTITY_VIDEO_STREAM
        request.view_parameters.to_session( request )
        
        return {
            'entity': entity,
            'sensor': sensor,
            'current_history': current_history,
            'timeline_groups': timeline_groups,
            'prev_history': prev_history,
            'next_history': next_history,
            'sensor_history_items': mock_history_items,
        }
    
    def _create_mock_sensor_history( self, sensor, current_id=None ):
        """Create mock sensor history data for Phase 1 demonstration."""
        now = datetime.now()
        mock_items = []
        
        # Create 15 mock history items over the past 3 days
        for i in range(15):
            # Create timestamps with varying intervals
            if i < 5:
                # Recent items within last few hours
                timestamp = now - timedelta(hours=i * 2, minutes=i * 15)
            elif i < 10:
                # Yesterday's items
                timestamp = now - timedelta(days=1, hours=i - 5, minutes=i * 10)
            else:
                # Older items
                timestamp = now - timedelta(days=2 + (i - 10) * 0.5, hours=(i - 10) * 3)
            
            mock_items.append({
                'id': 1000 + i,  # Mock IDs
                'sensor': sensor,
                'value': 'active' if i % 3 == 0 else 'idle',
                'timestamp': timestamp,
                'duration_seconds': 60 + (i * 15),  # Mock duration
                'has_video_stream': True,
                'mock_video_url': f'/static/mock/video_{i}.mp4',  # Placeholder URL
                'details': f'Motion detected in {sensor.entity_state.entity.name}' if i % 3 == 0 else 'No activity'
            })
        
        return mock_items
    
    def _group_history_by_time( self, history_items ):
        """Group history items by time period for timeline display."""
        if not history_items:
            return []
        
        groups = []
        current_date = None
        current_hour = None
        current_group = None
        
        # Determine if we should group by hour (if many events) or by day
        today = datetime.now().date()
        today_count = sum(1 for h in history_items if h['timestamp'].date() == today)
        use_hourly = today_count > 10
        
        for item in history_items:
            item_date = item['timestamp'].date()
            item_hour = item['timestamp'].hour
            
            # Create new group if needed
            if use_hourly and item_date == today:
                # Group by hour for today if many events
                if current_date != item_date or current_hour != item_hour:
                    current_date = item_date
                    current_hour = item_hour
                    current_group = {
                        'label': f"{item['timestamp'].strftime('%I:00 %p')}",
                        'date': item_date,
                        'items': []
                    }
                    groups.append(current_group)
            else:
                # Group by day
                if current_date != item_date:
                    current_date = item_date
                    current_hour = None
                    if item_date == today:
                        label = "Today"
                    elif item_date == today - timedelta(days=1):
                        label = "Yesterday"
                    else:
                        label = item['timestamp'].strftime('%B %d')
                    
                    current_group = {
                        'label': label,
                        'date': item_date,
                        'items': []
                    }
                    groups.append(current_group)
            
            if current_group:
                current_group['items'].append(item)
        
        return groups

        
class ConsoleLockView( View ):

    def post( self, request, *args, **kwargs ):
        lock_password = ConsoleSettingsHelper().get_console_lock_password()
        if not lock_password:
            return SetLockPasswordView().get( request, *args, **kwargs )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class SetLockPasswordView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'console/modals/set_lock_password.html'
    
    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
    def post( self, request, *args, **kwargs ):
        input_password = request.POST.get('password')
        if not input_password:
            raise BadRequest( 'No password provided.' )
        ConsoleSettingsHelper().set_console_lock_password( password = input_password )
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return ConsoleUnlockView().get( request, *args, **kwargs )

    
class ConsoleUnlockView( HiModalView ):

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

        lock_password = ConsoleSettingsHelper().get_console_lock_password()

        if lock_password and ( input_password != lock_password ):
            raise BadRequest( 'Invalid password.' )
                               
        # N.B. It should not be possible to get into state where console is
        # locked without a password set.  However, if it happens, it would
        # be impossible to unlock the console. Thus, we'll unlock in that
        # exceptional case.

        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = False
        return self.refresh_response( request= request )
