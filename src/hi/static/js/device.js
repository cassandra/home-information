(function() {

    window.Hi = window.Hi || {};

    /*
      DEVICE CAPABILITIES

      - Markup declares what an element needs via Hi.DEVICE_REQUIRES_ATTR
        (space-separated capability names, e.g. "local_files browser_nav").
      - Markup may also name in-app handlers that can stand in for a
        missing capability via Hi.DEVICE_REQUIRES_HANDLER_ATTR (e.g.
        "on-screen-keyboard"). A handler module registers itself, and the
        capability it stands in for, when it loads; a declared handler
        that never registered meets nothing.
      - A requirement is unmet when the device lacks the capability and
        no declared, registered handler stands in for it.
      - Capture-phase listeners block any such action when a requirement
        is unmet and ask the server for the explanatory modal. Capture
        phase runs before inline onclick handlers, jQuery delegated
        handlers, default link navigation and antinode async actions.
        Being registered from js_before_content, it also runs before
        document-level capture listeners registered later (e.g.
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
        registerHandler: function( handlerName, capabilityName ) {
            _registerHandler( handlerName, capabilityName );
        },
        getUnmetRequirements: function( requiresValue, handlersValue ) {
            return _getUnmetRequirements( requiresValue, handlersValue );
        },
        isHandlerActiveFor: function( handlerName, element ) {
            return _isHandlerActiveFor( handlerName, element );
        }
    };

    window.Hi.device = HiDevice;

    // Handler name -> the capability name it stands in for.
    const _handlerCapabilities = {};

    function _isAvailable( capabilityName ) {
        return Hi.deviceCapabilities[capabilityName] !== false;
    }

    function _registerHandler( handlerName, capabilityName ) {
        _handlerCapabilities[handlerName] = capabilityName;
    }

    function _parseNames( attrValue ) {
        return ( attrValue || '' ).split( /\s+/ ).filter( Boolean );
    }

    function _getHandledCapabilities( handlersValue ) {
        return _parseNames( handlersValue )
            .filter( function( handlerName ) {
                return Object.prototype.hasOwnProperty.call( _handlerCapabilities, handlerName );
            })
            .map( function( handlerName ) {
                return _handlerCapabilities[handlerName];
            });
    }

    function _getUnmetRequirements( requiresValue, handlersValue ) {
        const handledCapabilities = _getHandledCapabilities( handlersValue );
        return _parseNames( requiresValue ).filter( function( capabilityName ) {
            return ! _isAvailable( capabilityName )
                && ! handledCapabilities.includes( capabilityName );
        });
    }

    // True when the element relies on this handler right now: it declares
    // the handler, requires the capability the handler stands in for, and
    // the device lacks that capability.
    function _isHandlerActiveFor( handlerName, element ) {
        if ( ! Object.prototype.hasOwnProperty.call( _handlerCapabilities, handlerName )) {
            return false;
        }
        const capabilityName = _handlerCapabilities[handlerName];
        return _parseNames( element.getAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR )).includes( handlerName )
            && _parseNames( element.getAttribute( Hi.DEVICE_REQUIRES_ATTR )).includes( capabilityName )
            && ! _isAvailable( capabilityName );
    }

    function _showUnavailableModal( unmetRequirements ) {
        const params = new URLSearchParams();
        unmetRequirements.forEach( function( name ) {
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
        const unmetRequirements = _getUnmetRequirements(
            requiringElement.getAttribute( Hi.DEVICE_REQUIRES_ATTR ),
            requiringElement.getAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR )
        );
        if ( unmetRequirements.length === 0 ) {
            return;
        }
        event.preventDefault();
        event.stopImmediatePropagation();
        _showUnavailableModal( unmetRequirements );
    }

    document.addEventListener( 'click', _gateAction, true );

    // auxclick also fires for the right button; leave context menus alone.
    document.addEventListener( 'auxclick', function( event ) {
        if ( event.button === MIDDLE_MOUSE_BUTTON ) {
            _gateAction( event );
        }
    }, true );

})();
