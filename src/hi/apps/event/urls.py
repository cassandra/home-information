from django.urls import path
from django.urls import include

from . import views


urlpatterns = [

    path( 'definitions', 
          views.EventDefinitionsView.as_view(), 
          name='event_definitions'),

    path( 'history', 
          views.EventHistoryView.as_view(), 
          name='event_history'),

    path( 'edit/', include('hi.apps.event.edit.urls' )),

]
