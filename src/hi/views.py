from django.shortcuts import render
from django.views.generic import View

from hi.apps.location.models import Location


def home_javascript_files( request, filename ):
    return render(request, filename, {}, content_type = "text/javascript")


class HomeView( View ):

    def get(self, request, *args, **kwargs):

        location = Location.objects.order_by( 'order_id' ).first()
        location_view_list = list( location.views.order_by( 'order_id' ))
        current_location_view = location_view_list[0]
        
        context = {
            'current_location_view': current_location_view,
            'location_view_list': location_view_list,
        }
        return render( request, 'pages/home.html', context )
