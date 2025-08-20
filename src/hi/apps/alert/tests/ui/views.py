from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.alert.enums import AlarmLevel
from hi.apps.alert.tests.synthetic_data import AlertSyntheticData
from hi.apps.alert.views import AlertDetailsView


class TestUiAlertHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "alert/tests/ui/home.html", context )

    
class TestUiAlertDetailsView( AlertDetailsView, AlertMixin ):
    """
    View for testing alert details dialogs with various synthetic data scenarios.
    Uses the centralized AlertSyntheticData class for consistent test data generation.
    """

    def get( self, request, *args, **kwargs ):
        alert_type = kwargs.get('alert_type')
        
        # Create synthetic alert based on type using centralized synthetic data
        alert = self._create_synthetic_alert( alert_type )
        
        # Store alert in alert manager for retrieval 
        alert_manager = self.alert_manager()
        alert_manager._alert_queue._alert_list.append(alert)
        
        # Use parent class logic with synthetic alert
        kwargs['alert_id'] = alert.id
        return super().get( request, *args, **kwargs )

    def _create_synthetic_alert( self, alert_type ):
        """Create different types of synthetic alerts for testing using AlertSyntheticData."""
        
        if alert_type == 'single_info':
            return AlertSyntheticData.create_single_alarm_alert(
                alarm_level = AlarmLevel.INFO,
                has_image = False
            )
        elif alert_type == 'single_warning_image':
            return AlertSyntheticData.create_single_alarm_alert(
                alarm_level = AlarmLevel.WARNING,
                has_image = True,
                detail_attrs = {'Location': 'Kitchen', 'Sensor': 'Motion-01', 'Image': 'Captured'}
            )
        elif alert_type == 'single_critical_video':
            return AlertSyntheticData.create_single_alarm_alert(
                alarm_level = AlarmLevel.CRITICAL,
                has_image = True,
                detail_attrs = {
                    'Location': 'Kitchen', 
                    'Camera': 'Kitchen Camera',
                    'Motion Detected': 'Yes',
                    'Video Stream': 'Available'
                }
            )
        elif alert_type == 'multiple_alarms':
            return AlertSyntheticData.create_multiple_alarm_alert(
                alarm_count = 3,
                has_image = True
            )
        elif alert_type == 'event_based':
            return AlertSyntheticData.create_event_based_alert(
                has_image = True
            )
        elif alert_type == 'weather_alert':
            return AlertSyntheticData.create_weather_alert(
                has_image = False
            )
        else:
            raise BadRequest( f'Unknown alert type: {alert_type}' )
