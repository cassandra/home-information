from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.alert.enums import AlarmLevel
from hi.apps.alert.tests.synthetic_data import AlertSyntheticData


class TestUiAlertHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "alert/tests/ui/home.html", context )

    
class TestUiAlertDetailsView( View ):
    """
    View for testing alert details dialogs with various synthetic data scenarios.
    Uses the centralized AlertSyntheticData class for consistent test data generation.
    Renders the template directly without modifying system state.
    """

    def get( self, request, *args, **kwargs ):
        alert_type = kwargs.get('alert_type')
        
        # Create synthetic alert based on type using centralized synthetic data
        alert = self._create_synthetic_alert( alert_type )
        
        # Prepare visual content data for template (same logic as AlertDetailsView)
        visual_content = self._get_first_visual_content( alert )
        
        # Render template directly with synthetic data
        context = {
            'alert': alert,
            'alert_visual_content': visual_content,
        }
        return render( request, 'alert/modals/alert_details.html', context )
    
    def _get_first_visual_content( self, alert ):
        """
        Find the first image/video content from any alarm in the alert.
        Returns dict with image info or None if no visual content found.
        """
        for alarm in alert.alarm_list:
            for source_details in alarm.source_details_list:
                if source_details.image_url:
                    return {
                        'image_url': source_details.image_url,
                        'alarm': alarm,
                        'is_from_latest': alarm == alert.alarm_list[0] if alert.alarm_list else False,
                    }
        return None

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
