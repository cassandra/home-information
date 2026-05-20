from django.urls import path

from . import views


urlpatterns = [
    path( '<str:module_key>/create',
          views.CreateProfileView.as_view(),
          name = 'simulator_profile_create' ),

    path( '<str:module_key>/edit/<int:profile_id>',
          views.EditProfileView.as_view(),
          name = 'simulator_profile_edit' ),

    path( '<str:module_key>/clone/<int:profile_id>',
          views.CloneProfileView.as_view(),
          name = 'simulator_profile_clone' ),

    path( '<str:module_key>/delete/<int:profile_id>',
          views.DeleteProfileView.as_view(),
          name = 'simulator_profile_delete' ),

    path( '<str:module_key>/switch/<int:profile_id>',
          views.SwitchProfileView.as_view(),
          name = 'simulator_profile_switch' ),
]
