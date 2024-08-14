from django.shortcuts import render
from django.views.generic import View

from .models import LocationView


class LocationViewView( View ):

    def get(self, request, *args, **kwargs):

        location_view_id = kwargs.get('id')
        current_location_view = LocationView.objects.select_related( 'location' ).get( id = location_view_id )
        context = {
            'current_location_view': current_location_view,
        }
        return render( request, 'location/location_view.html', context )
