from django.urls import path

from . import views


urlpatterns = [

    path( 'definition/add', 
          views.EventDefinitionAddView.as_view(), 
          name='event_definition_add'),

    path( 'definition/edit/<int:id>', 
          views.EventDefinitionEditView.as_view(), 
          name='event_definition_edit'),

    path( 'definition/delete/<int:id>', 
          views.EventDefinitionDeleteView.as_view(), 
          name='event_definition_delete'),

]
