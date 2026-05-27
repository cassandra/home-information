class NoStoreMiddleware:
    """Set ``Cache-Control: no-store`` on dynamic HTML and JSON
    responses.

    Without an explicit cache directive, browsers apply heuristic
    caching to HTML and may serve a previously-rendered page from
    cache when the server is unreachable — controls in the cached
    JS appear to work but every AJAX call silently fails. ``no-store``
    opts out so a reload while the server is down shows the browser's
    native error page, not a deceptive working-looking UI.

    Static assets (CSS, JS, images, fonts) are untouched — their
    content type doesn't match, and they should remain cacheable.
    Views that explicitly set ``Cache-Control`` (e.g. streaming
    endpoints with their own directives) are respected.

    Mirrors ``hi.middleware.NoStoreMiddleware``; the simulator is a
    separate Django app with deliberately minimal sharing, so it
    carries its own copy rather than importing from the main app.
    """

    _DYNAMIC_CONTENT_PREFIXES = ( 'text/html', 'application/json' )

    def __init__( self, get_response ):
        self.get_response = get_response
        return

    def __call__( self, request ):
        response = self.get_response( request )
        if response.has_header( 'Cache-Control' ):
            return response
        content_type = response.get( 'Content-Type', '' )
        for prefix in self._DYNAMIC_CONTENT_PREFIXES:
            if content_type.startswith( prefix ):
                response[ 'Cache-Control' ] = 'no-store'
                break
        return response
