from django.http import HttpRequest

from .constants import ConsoleConstants


class SleepModeCookie:
    """
    Persistence of sleep mode, so it survives page reloads and browser
    restarts. The client sets the cookie on sleep and deletes it on wake;
    its presence alone means sleep mode is active.
    """

    NAME = ConsoleConstants.SLEEP_MODE_COOKIE_NAME

    @classmethod
    def is_active( cls, request : HttpRequest ) -> bool:
        return cls.NAME in request.COOKIES
