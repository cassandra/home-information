from django.urls import re_path

from . import views


urlpatterns = [
    re_path( r'^search/(?P<integration_id>[\w\-]+)$',
             views.AttributeReferenceSearchView.as_view(),
             name='integrations_attribute_reference_search' ),
    re_path( r'^attach/(?P<integration_id>[\w\-]+)$',
             views.AttributeReferenceAttachView.as_view(),
             name='integrations_attribute_reference_attach' ),
]
