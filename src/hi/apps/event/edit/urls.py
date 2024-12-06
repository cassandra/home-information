from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^definition/add$', 
             views.EventDefinitionAddView.as_view(), 
             name='event_definition_add'),

    re_path( r'^definition/edit/(?P<id>\d+)$', 
             views.EventDefinitionEditView.as_view(), 
             name='event_definition_edit'),

    re_path( r'^definition/delete/(?P<id>\d+)$', 
             views.EventDefinitionDeleteView.as_view(), 
             name='event_definition_delete'),

]
