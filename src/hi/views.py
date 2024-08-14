from django.shortcuts import render
from django.views.generic import View


class HomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render( request, 'pages/home.html', context )

