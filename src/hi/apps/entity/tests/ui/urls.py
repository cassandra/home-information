from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$',
            views.TestUiEntityHomeView.as_view(),
            name='entity_tests_ui'),

    re_path(r'^visual-browser/$',
            views.TestUiEntityTypeVisualBrowserView.as_view(),
            name='test_entity_type_visual_browser'),
]
