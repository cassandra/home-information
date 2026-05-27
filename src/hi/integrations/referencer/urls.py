from django.urls import path, re_path

from . import views


urlpatterns = [
    path( 'picker/',
          views.AttributeReferencePickerView.as_view(),
          name='integrations_attribute_reference_picker' ),

    path( 'home/',
          views.ReferenceHomeView.as_view(),
          name='integrations_reference_home' ),

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$',
             views.ReferenceManageView.as_view(),
             name='integrations_reference_manage' ),
]
