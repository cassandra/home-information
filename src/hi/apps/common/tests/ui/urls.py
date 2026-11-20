from django.urls import path

from . import views


urlpatterns = [
    path('',
         views.TestUiCommonHomeView.as_view(), 
         name='common_tests_ui'),

    path('icons',
         views.TestUiIconBrowserView.as_view(), 
         name='common_tests_ui_icons'),

    path('file-viewer',
         views.TestUiFileViewerView.as_view(),
         name='common_tests_ui_file_viewer'),
]
