from django.urls import re_path
from . import views

urlpatterns = [

    re_path( r'^initialize/custom$', 
             views.InitializeCustomView.as_view(), 
             name='profiles_initialize_custom'),

    re_path( r'^initialize/prefined/(?P<profile_type>\w+)/$', 
             views.InitializePredefinedView.as_view(), 
             name='profiles_initialize_predefined'),
    
    re_path( r'^view-reference-help$', 
             views.ViewReferenceHelpView.as_view(), 
             name='profiles_view_reference_help'),
    
    re_path( r'^edit-reference-help$', 
             views.EditReferenceHelpView.as_view(), 
             name='profiles_edit_reference_help'),
    
]
