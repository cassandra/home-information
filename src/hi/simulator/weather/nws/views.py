import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

import hi.apps.common.antinode as antinode
import hi.apps.common.datetimeproxy as datetimeproxy

from .forms import NwsSimAlertForm
from .models import NwsSimAlert

logger = logging.getLogger(__name__)


class NwsAlertsActiveView( View ):
    """NWS-shaped /alerts/active endpoint backed by NwsSimAlert rows."""

    def get( self, request, *args, **kwargs ):
        features : List[ Dict[str, Any] ] = []
        now = datetimeproxy.now()
        for alert in NwsSimAlert.objects.filter( is_active = True ):
            effective = now + timedelta( seconds = alert.effective_offset_secs )
            expires = now + timedelta( seconds = alert.expires_offset_secs )
            properties : Dict[ str, Any ] = {
                'event': alert.event_name,
                'headline': alert.headline,
                'description': alert.description,
                'instruction': alert.instruction,
                'areaDesc': alert.area_desc,
                'status': alert.status_str,
                'severity': alert.severity_str,
                'urgency': alert.urgency_str,
                'certainty': alert.certainty_str,
                'category': alert.category_str,
                'effective': effective.isoformat(),
                'expires': expires.isoformat(),
                'onset': effective.isoformat(),
                'ends': expires.isoformat(),
            }
            if alert.event_code:
                properties['eventCode'] = {
                    'NationalWeatherService': [ alert.event_code ],
                }
            # Feature id changes on each row save (toggle / edit) so
            # the main app treats each issuance as distinct, matching
            # real NWS where every Update / Cancel publishes a new
            # identifier. Repeat polls of an unchanged row share the
            # same id.
            issuance = int( alert.updated_datetime.timestamp() )
            features.append({
                'id': f'sim-nws-alert-{alert.id}-{issuance}',
                'properties': properties,
            })
        return JsonResponse( { 'features': features } )


class NwsSimAlertAddView( View ):

    MODAL_TEMPLATE = 'simulator/weather/nws/modals/alert_form.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'form': NwsSimAlertForm(),
            'is_add': True,
        }
        return render( request, self.MODAL_TEMPLATE, context )

    def post( self, request, *args, **kwargs ):
        form = NwsSimAlertForm( request.POST )
        if not form.is_valid():
            return render( request, self.MODAL_TEMPLATE, {
                'form': form,
                'is_add': True,
            })
        form.save()
        return antinode.refresh_response()


class NwsSimAlertEditView( View ):

    MODAL_TEMPLATE = 'simulator/weather/nws/modals/alert_form.html'

    def get( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        context = {
            'form': NwsSimAlertForm( instance = alert ),
            'alert': alert,
            'is_add': False,
        }
        return render( request, self.MODAL_TEMPLATE, context )

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        form = NwsSimAlertForm( request.POST, instance = alert )
        if not form.is_valid():
            return render( request, self.MODAL_TEMPLATE, {
                'form': form,
                'alert': alert,
                'is_add': False,
            })
        form.save()
        return antinode.refresh_response()


class NwsSimAlertDeleteView( View ):

    MODAL_TEMPLATE = 'simulator/weather/nws/modals/alert_delete.html'

    def get( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        return render( request, self.MODAL_TEMPLATE, { 'alert': alert })

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        alert.delete()
        return antinode.refresh_response()


class NwsSimAlertToggleView( View ):

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        alert.is_active = not alert.is_active
        alert.save( update_fields = [ 'is_active' ] )
        return antinode.refresh_response()
