from django.urls import path
from django.urls import re_path

from . import views

urlpatterns = [

    path( 'v1/users/login',
          views.LoginView.as_view(),
          name = 'homebox_api_login' ),

    # v0.25 legacy ``items`` family.
    path( 'v1/items',
          views.AllItemsView.as_view(),
          name = 'homebox_api_items' ),

    re_path( r'^v1/items/(?P<item_id>[\w\-]+)$',
             views.ItemDetailView.as_view(),
             name = 'homebox_api_item_detail' ),

    re_path( r'^v1/items/(?P<item_id>[\w\-]+)/attachments/(?P<attachment_id>[\w\-]+)$',
             views.AttachmentDownloadView.as_view(),
             name = 'homebox_api_attachment_download' ),

    # v0.26 ``entities`` family. Each view 404s when the simulator
    # is in v0.25 mode so the integration's version probe sees the
    # legacy fallback correctly.
    path( 'v1/entities',
          views.AllEntitiesView.as_view(),
          name = 'homebox_api_entities' ),

    re_path( r'^v1/entities/(?P<entity_id>[\w\-]+)$',
             views.EntityDetailView.as_view(),
             name = 'homebox_api_entity_detail' ),

    re_path( r'^v1/entities/(?P<entity_id>[\w\-]+)/attachments/(?P<attachment_id>[\w\-]+)$',
             views.EntityAttachmentDownloadView.as_view(),
             name = 'homebox_api_entity_attachment_download' ),
]
