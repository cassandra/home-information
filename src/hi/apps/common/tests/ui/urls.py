from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^$',
            views.TestUiCommonHomeView.as_view(), 
            name='common_tests_ui'),

    re_path(r'^icons$',
            views.TestUiIconBrowserView.as_view(), 
            name='common_tests_ui_icons'),
]
