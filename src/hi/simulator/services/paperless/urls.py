from django.urls import path

from . import views


urlpatterns = [

    path( 'api/documents/',
          views.DocumentsListView.as_view(),
          name = 'paperless_documents_list' ),

    path( 'api/documents/<int:document_id>/thumb/',
          views.ThumbnailView.as_view(),
          name = 'paperless_document_thumbnail' ),

    path( 'api/documents/<int:document_id>/download/',
          views.DownloadView.as_view(),
          name = 'paperless_document_download' ),

    path( 'documents/<int:document_id>/details/',
          views.PreviewView.as_view(),
          name = 'paperless_document_preview' ),

    path( 'settings/set/',
          views.SetSettingsView.as_view(),
          name = 'paperless_settings_set' ),
]
