from django.urls import path, re_path

from . import views


urlpatterns = [
    path( 'picker/',
          views.ExternalReferencePickerView.as_view(),
          name='integrations_external_reference_picker' ),

    path( 'picker/search/',
          views.ExternalReferenceSearchView.as_view(),
          name='integrations_external_reference_search' ),

    path( 'picker/attach/',
          views.ExternalReferenceAttachView.as_view(),
          name='integrations_external_reference_attach' ),

    path( 'home/',
          views.ReferenceHomeView.as_view(),
          name='integrations_reference_home' ),

    re_path( r'^manage/(?P<integration_id>[\w\-]*)$',
             views.ReferenceManageView.as_view(),
             name='integrations_reference_manage' ),
]
