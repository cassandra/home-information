from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^definitions$', 
             views.EventDefinitionsView.as_view(), 
             name='event_definitions'),

    re_path( r'^edit/', include('hi.apps.event.edit.urls' )),

]
