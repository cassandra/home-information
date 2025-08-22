from django.shortcuts import render
from django.views.generic import View


class TestingHomeView( View ):
    
    def get(self, request, *args, **kwargs):
        return render( request, 'testing/pages/testing_home.html' )
