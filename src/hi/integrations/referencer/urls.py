from django.urls import path

from . import views


urlpatterns = [
    path( 'picker/',
          views.AttributeReferencePickerView.as_view(),
          name='integrations_attribute_reference_picker' ),
]
