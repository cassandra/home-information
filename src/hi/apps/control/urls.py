from django.urls import path

from . import views


urlpatterns = [

    path( 'controller/<int:controller_id>',
          views.ControllerView.as_view(),
          name='control_controller'),
]
