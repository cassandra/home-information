
from django.conf import settings

from .constants import DIVID


def constants_context(request):
    return {
        'DIVID': DIVID,
        'STATIC_URL': settings.STATIC_URL,
    }
