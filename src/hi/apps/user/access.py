from django.conf import settings
from django.http import HttpRequest


def has_content_access( request : HttpRequest ) -> bool:
    """ Whether the request may see app content (vs. only the sign-in flow). """
    return settings.SUPPRESS_AUTHENTICATION or request.user.is_authenticated
