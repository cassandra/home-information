from django.urls import path

from . import views


urlpatterns = [
    path('', 
         views.EnvironmentHomeView.as_view(), 
         name='env_home'),
]
