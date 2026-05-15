from django.urls import path

from . import views


urlpatterns = [

    path( 'acknowledge/<path:alert_id>', 
          views.AlertAcknowledgeView.as_view(), 
          name='alert_acknowledge'),

    path( 'details/<path:alert_id>', 
          views.AlertDetailsView.as_view(), 
          name='alert_details'),
]
