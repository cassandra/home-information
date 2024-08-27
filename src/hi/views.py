from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View


def home_javascript_files( request, filename ):
    return render(request, filename, {}, content_type = "text/javascript")


class HomeView( View ):

    def get(self, request, *args, **kwargs):

        redirect_url = reverse( 'location_view_default' )
        return HttpResponseRedirect( redirect_url )
