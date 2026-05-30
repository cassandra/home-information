from django.urls import path

from .views import ImmichThumbnailProxyView


urlpatterns = [
    path(
        'assets/<str:asset_id>/thumb/',
        ImmichThumbnailProxyView.as_view(),
        name = 'immich_thumbnail',
    ),
]
