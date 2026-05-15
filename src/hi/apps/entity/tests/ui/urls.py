from django.urls import path
from . import views

urlpatterns = [
    path('',
         views.TestUiEntityHomeView.as_view(),
         name='entity_tests_ui'),

    path('visual-browser/',
         views.TestUiEntityTypeVisualBrowserView.as_view(),
         name='test_entity_type_visual_browser'),
]
