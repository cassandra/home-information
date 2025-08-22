from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^history/(?P<attribute_id>\d+)/$', 
            views.AttributeHistoryView.as_view(), 
            name='attribute_history'),
    re_path(r'^restore/(?P<attribute_id>\d+)/$', 
            views.AttributeRestoreView.as_view(), 
            name='attribute_restore'),
]
