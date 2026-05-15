from django.urls import path
from django.urls import re_path
from . import views

urlpatterns = [

    path( 'initialize/custom', 
          views.InitializeCustomView.as_view(), 
          name='profiles_initialize_custom'),

    re_path( r'^initialize/prefined/(?P<profile_type>\w+)/$', 
             views.InitializePredefinedView.as_view(), 
             name='profiles_initialize_predefined'),
    
    path( 'view-reference-help', 
          views.ViewReferenceHelpView.as_view(), 
          name='profiles_view_reference_help'),
    
    path( 'edit-reference-help',
          views.EditReferenceHelpView.as_view(),
          name='profiles_edit_reference_help'),

    path( 'dismiss-view-intro-help',
          views.DismissViewIntroHelpView.as_view(),
          name='profiles_dismiss_view_intro_help'),

]
