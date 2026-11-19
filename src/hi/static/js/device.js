(function() {

    window.Hi = window.Hi || {};

    /*
      DEVICE CAPABILITIES

      - Markup declares what an action needs via Hi.DEVICE_REQUIRES_ATTR
        (space-separated capability names, e.g. "local_files browser_nav").
      - Capture-phase listeners block any such action when a required
        capability is missing and ask the server for the explanatory
        modal. Capture phase runs before inline onclick handlers, jQuery
        delegated handlers, default link navigation and antinode async
        actions. Being registered from js_before_content, it also runs
        before document-level capture listeners registered later (e.g.
        attr-unsaved-guard.js).
      - Middle-click opens links in a new tab via auxclick, not click, so
        that is gated too. Browser-native long-press "open in new tab"
        menus cannot be intercepted reliably.
    */

    const MIDDLE_MOUSE_BUTTON = 1;

    const HiDevice = {
        isAvailable: function( capabilityName ) {
            return _isAvailable( capabilityName );
        },
        getMissingCapabilities: function( requiresValue ) {
            return _getMissingCapabilities( requiresValue );
        }
    };

    window.Hi.device = HiDevice;

    function _isAvailable( capabilityName ) {
        return Hi.deviceCapabilities[capabilityName] !== false;
    }

    function _getMissingCapabilities( requiresValue ) {
        if ( ! requiresValue ) {
            return [];
        }
        return requiresValue.trim().split( /\s+/ ).filter( function( name ) {
            return ! _isAvailable( name );
        });
    }

    function _showUnavailableModal( missingCapabilities ) {
        const params = new URLSearchParams();
        missingCapabilities.forEach( function( name ) {
            params.append( Hi.DEVICE_REQUIRES_FIELD, name );
        });
        AN.get( Hi.DEVICE_CAPABILITY_UNAVAILABLE_URL + '?' + params.toString() );
    }

    function _gateAction( event ) {
        if ( ! ( event.target instanceof Element )) {
            return;
        }
        const requiringElement = event.target.closest( '[' + Hi.DEVICE_REQUIRES_ATTR + ']' );
        if ( ! requiringElement ) {
            return;
        }
        const missingCapabilities = _getMissingCapabilities(
            requiringElement.getAttribute( Hi.DEVICE_REQUIRES_ATTR )
        );
        if ( missingCapabilities.length === 0 ) {
            return;
        }
        event.preventDefault();
        event.stopImmediatePropagation();
        _showUnavailableModal( missingCapabilities );
    }

    document.addEventListener( 'click', _gateAction, true );

    // auxclick also fires for the right button; leave context menus alone.
    document.addEventListener( 'auxclick', function( event ) {
        if ( event.button === MIDDLE_MOUSE_BUTTON ) {
            _gateAction( event );
        }
    }, true );

})();
