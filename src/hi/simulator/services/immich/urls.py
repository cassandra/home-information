from django.urls import path

from . import views


urlpatterns = [

    path( 'api/search/smart',
          views.SmartSearchView.as_view(),
          name = 'immich_search_smart' ),

    path( 'api/search/metadata',
          views.MetadataSearchView.as_view(),
          name = 'immich_search_metadata' ),

    path( 'api/assets/<str:asset_id>/thumbnail',
          views.ThumbnailView.as_view(),
          name = 'immich_asset_thumbnail' ),

    path( 'photos/<str:asset_id>',
          views.PhotoPreviewView.as_view(),
          name = 'immich_photo_preview' ),

    path( 'settings/set/',
          views.SetSettingsView.as_view(),
          name = 'immich_settings_set' ),
]
