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
      - Scope differs by purpose. The click gate honors the nearest
        declaring ancestor (e.g. a link wrapping an icon). A handler acts
        only on an element that itself declares the requirement and the
        handler (isHandlerActiveFor), so declare handler-served
        requirements on the field, not on a container: a container
        declaration would pass the gate yet never engage the handler.
      - Text-entry controls (KEYBOARD_ENTRY_INPUT_TYPES and textarea)
        that declare nothing themselves require the keyboard by default,
        unless disabled or read-only. A control's own declaration
        replaces the default (e.g. to name the on-screen keyboard
        handler); otherwise its default comes before any declaring
        ancestor. getUnmetRequirementsFor resolves this for an element,
        so other modules can ask before acting on a field
        programmatically (e.g. focusing it), which the click gate never
        sees.
      - A requirement is unmet when the device lacks the capability and
        no declared, registered handler stands in for it.
      - Capture-phase listeners block any such action when a requirement
        is unmet and ask the server for the explanatory modal. Capture
        phase runs before inline onclick handlers, jQuery delegated
        handlers, default link navigation and antinode async actions.
        Being registered from js_before_content, it also runs before
        document-level capture listeners registered later (e.g.
        attr-unsaved-guard.js). A tap focuses a control before its click
        arrives, so a blocked element that has focus is blurred.
      - Middle-click opens links in a new tab via auxclick, not click, so
        that is gated too. Browser-native long-press "open in new tab"
        menus cannot be intercepted reliably.
    */

    const MIDDLE_MOUSE_BUTTON = 1;
    const KEYBOARD_CAPABILITY_NAME = 'keyboard';

    // Input types whose value can only be typed. Others are operated
    // through native controls: number has step arrows (rendered wherever
    // a device lacks a system keyboard), and checkbox, range, date,
    // color, etc. have their own.
    const KEYBOARD_ENTRY_INPUT_TYPES = new Set([
        'text', 'email', 'password', 'search', 'url', 'tel'
    ]);

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
        getUnmetRequirementsFor: function( element ) {
            return _getUnmetRequirementsFor( element );
        },
        isHandlerActiveFor: function( handlerName, element ) {
            return _isHandlerActiveFor( handlerName, element );
        }
    };

    window.Hi.device = HiDevice;

    // Handler name -> the capability name it stands in for.
    const _handlerCapabilities = new Map();

    function _isAvailable( capabilityName ) {
        return Hi.deviceCapabilities[capabilityName] !== false;
    }

    function _registerHandler( handlerName, capabilityName ) {
        _handlerCapabilities.set( handlerName, capabilityName );
    }

    function _parseNames( attrValue ) {
        return ( attrValue || '' ).split( /\s+/ ).filter( Boolean );
    }

    function _getHandledCapabilities( handlersValue ) {
        return _parseNames( handlersValue )
            .filter( function( handlerName ) {
                return _handlerCapabilities.has( handlerName );
            })
            .map( function( handlerName ) {
                return _handlerCapabilities.get( handlerName );
            });
    }

    function _getUnmetRequirements( requiresValue, handlersValue ) {
        const handledCapabilities = _getHandledCapabilities( handlersValue );
        return _parseNames( requiresValue ).filter( function( capabilityName ) {
            return ! _isAvailable( capabilityName )
                && ! handledCapabilities.includes( capabilityName );
        });
    }

    function _isKeyboardEntryControl( element ) {
        const isEntryControl = ( element instanceof HTMLTextAreaElement )
              || (( element instanceof HTMLInputElement )
                  && KEYBOARD_ENTRY_INPUT_TYPES.has( element.type ));
        return isEntryControl && ! element.disabled && ! element.readOnly;
    }

    function _hasDeclaration( element ) {
        return element.hasAttribute( Hi.DEVICE_REQUIRES_ATTR );
    }

    // The element whose requirements govern actions on the given one:
    // itself if it declares or has a default, else the nearest declaring
    // ancestor, else null.
    function _findRequiringElement( element ) {
        if ( ! _hasDeclaration( element ) && _isKeyboardEntryControl( element )) {
            return element;
        }
        return element.closest( '[' + Hi.DEVICE_REQUIRES_ATTR + ']' );
    }

    function _getUnmetRequirementsOf( requiringElement ) {
        if ( ! _hasDeclaration( requiringElement )) {
            return _getUnmetRequirements( KEYBOARD_CAPABILITY_NAME, null );
        }
        return _getUnmetRequirements(
            requiringElement.getAttribute( Hi.DEVICE_REQUIRES_ATTR ),
            requiringElement.getAttribute( Hi.DEVICE_REQUIRES_HANDLER_ATTR )
        );
    }

    function _getUnmetRequirementsFor( element ) {
        const requiringElement = _findRequiringElement( element );
        return requiringElement ? _getUnmetRequirementsOf( requiringElement ) : [];
    }

    // True when the element relies on this handler right now: it declares
    // the handler, requires the capability the handler stands in for, and
    // the device lacks that capability.
    function _isHandlerActiveFor( handlerName, element ) {
        if ( ! _handlerCapabilities.has( handlerName )) {
            return false;
        }
        const capabilityName = _handlerCapabilities.get( handlerName );
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
        const requiringElement = _findRequiringElement( event.target );
        if ( ! requiringElement ) {
            return;
        }
        const unmetRequirements = _getUnmetRequirementsOf( requiringElement );
        if ( unmetRequirements.length === 0 ) {
            return;
        }
        event.preventDefault();
        event.stopImmediatePropagation();
        if ( document.activeElement === requiringElement ) {
            requiringElement.blur();
        }
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
