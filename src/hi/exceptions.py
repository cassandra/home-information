class ForceRedirectException( Exception ):

    def __init__(self, url, message = 'Force redirect' ):
        self._url = url
        super().__init__(message)
        return

    @property
    def url(self):
        return self._url


class ForceSynchronousException( Exception ):
    pass
