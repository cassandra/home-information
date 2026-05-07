from django.urls import re_path

from . import views

urlpatterns = [

    re_path( r'^v1/users/login$',
             views.LoginView.as_view(),
             name = 'homebox_api_login' ),

    re_path( r'^v1/items$',
             views.AllItemsView.as_view(),
             name = 'homebox_api_items' ),

    re_path( r'^v1/items/(?P<item_id>[\w\-]+)$',
             views.ItemDetailView.as_view(),
             name = 'homebox_api_item_detail' ),

    re_path( r'^v1/items/(?P<item_id>[\w\-]+)/attachments/(?P<attachment_id>[\w\-]+)$',
             views.AttachmentDownloadView.as_view(),
             name = 'homebox_api_attachment_download' ),
]
