from django.conf import settings
from django.http import JsonResponse
from django.views.generic import View


class EnvironmentHomeView(View):

    @classmethod
    def get_env_data_for_view(self):
        # We do not necessarily want to expose every setting item in a
        # view (e.g., passwords), so we pick and choose the safe ones here.
        return {
            'ENVIRONMENT': settings.ENV.environment_name,
            'VERSION': settings.ENV.VERSION,
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'DATABASES_NAME_PATH': settings.DATABASES['default']['NAME'],
            'REDIS_HOST': settings.REDIS_HOST,
            'REDIS_PORT': settings.REDIS_PORT,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            'SERVER_EMAIL': settings.SERVER_EMAIL,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_USE_SSL': settings.EMAIL_USE_SSL,
            'CORS_ALLOWED_ORIGINS': settings.CORS_ALLOWED_ORIGINS,
            'CONTENT_SECURITY_POLICY': settings.CONTENT_SECURITY_POLICY,
        }
        
    def get(self, request, *args, **kwargs):
        data = self.get_env_data_for_view()
        return JsonResponse( data, safe = False )
    
