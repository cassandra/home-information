class ForceRedirectException( Exception ):

    def __init__(self, url, message = f'Force redirect' ):
        self._url = url
        super().__init__(message)
        return

    @property
    def url(self):
        return self._url
