/*
 * Home Information — Entity-state polling-update dispatcher.
 *
 * Consumes the ``entityStateStatusMap`` from the polling response
 * and applies per-EntityState DOM updates. The map is keyed by
 * CSS class (the per-state ``hi-entity-state-{id}`` marker); each
 * entry may carry attribute updates, display-value updates, and
 * controller-widget value updates. All three are applied in one
 * pass per CSS class.
 *
 * Scoping contract: an element receives an update only when it has
 * BOTH the matching CSS class AND the marker attribute (``status``,
 * ``display-text``, etc.) on the same element. No descendant
 * propagation. Templates put the CSS class on the same element that
 * carries the display attribute the update should touch.
 *
 * After the universal apply pass, registered EntityStatusPanel
 * handlers run. Panels that need behavior beyond what the universal
 * dispatcher handles (e.g., a thermostat dial whose SVG marker
 * angles are computed from numeric values) register a handler via
 * ``Hi.statePanels.register``. The fallback flat-list rendering is
 * itself a panel; its panel JS registers a handler for the
 * flat-list-specific behaviors (checkbox status-text mirror, dimmer
 * preset buttons, etc.).
 */
(function() {
    'use strict';

    window.Hi = window.Hi || {};
    Hi.entityStateStatus = Hi.entityStateStatus || {};

    // EntityStatusPanel JS that wants to react to polling updates
    // beyond what CSS keyed on the ``status`` attribute can do
    // registers a handler here. Handlers receive the full statusMap
    // and scope their own work using the ``.hi-state-panel-<name>``
    // and ``.hi-entity-state-<id>`` classes already present in the
    // DOM. Handlers run after the universal apply pass.
    const panelHandlers = [];
    Hi.statePanels = Hi.statePanels || {
        register: function( handler ) {
            if ( typeof handler === 'function' ) panelHandlers.push( handler );
        }
    };

    // Sliders the user is actively dragging. Polling-driven value
    // updates skip these elements so a server refresh mid-drag
    // doesn't yank the thumb out from under the operator's fingers.
    const activeSliders = new WeakSet();

    Hi.entityStateStatus.apply = function( statusMap ) {
        if ( ! statusMap ) return;
        for ( const cssClass in statusMap ) {
            const entry = statusMap[ cssClass ];
            const $elements = $( '.' + cssClass );
            if ( $elements.length === 0 ) continue;
            if ( entry.attributes ) applyAttributes( $elements, entry.attributes );
            if ( entry.display_value ) applyDisplay( $elements, entry.display_value );
            if ( entry.controller ) applyControllerValue( $elements, entry.controller );
        }
        for ( const handler of panelHandlers ) {
            try {
                handler( statusMap );
            } catch ( e ) {
                console.error( 'EntityStatusPanel handler error:', e );
            }
        }
    };

    function applyAttributes( $elements, attrMap ) {
        for ( const attrName in attrMap ) {
            const attrValue = attrMap[ attrName ];
            if ( attrValue == null ) continue;
            $elements.filter( '[' + attrName + ']' ).each( function() {
                if ( $( this ).attr( attrName ) !== String( attrValue ) ) {
                    $( this ).attr( attrName, attrValue );
                }
            });
        }
    }

    function applyDisplay( $elements, displayValue ) {
        // Templates opt in to display refresh by tagging the same
        // element with the per-state CSS class AND one of
        // ``display-text``, ``display-magnitude``, ``display-unit``.
        // The attribute is presence-only; the polled
        // ``display_value`` field of the same name supplies the
        // text.
        if ( displayValue.text != null ) {
            setTextOnAttr( $elements, 'display-text', displayValue.text );
        }
        if ( displayValue.magnitude != null ) {
            setTextOnAttr( $elements, 'display-magnitude', String( displayValue.magnitude ) );
        }
        if ( displayValue.unit_symbol != null ) {
            setTextOnAttr( $elements, 'display-unit', displayValue.unit_symbol );
        }
    }

    function setTextOnAttr( $elements, attrName, text ) {
        $elements.filter( '[' + attrName + ']' ).each( function() {
            if ( $( this ).text() !== text ) {
                $( this ).text( text );
            }
        });
    }

    function applyControllerValue( $elements, controllerDict ) {
        const value = controllerDict.value;
        $elements.each( function() {
            applyValueToElement( this, value );
        });
    }

    function applyValueToElement( element, value ) {
        const tag = element.tagName;
        if ( tag === 'INPUT' ) {
            const type = element.type;
            if ( type === 'range' || type === 'number' || type === 'text' ) {
                if ( type === 'range' && activeSliders.has( element ) ) return;
                setIfDifferent( element, 'value', String( value ) );
                syncSliderDisplay( element );
                return;
            }
            if ( type === 'checkbox' ) {
                const checked = coerceCheckboxValue( element, value );
                if ( element.checked !== checked ) element.checked = checked;
                return;
            }
        }
        if ( tag === 'SELECT' ) {
            setIfDifferent( element, 'value', String( value ) );
            return;
        }
        // Other shapes (color picker, etc.) get their own branches
        // here as widgets are added. Silently no-op for unrelated
        // class-targeted elements (e.g., wrapper divs sharing the
        // class for CSS purposes) so they're unaffected.
    }

    function setIfDifferent( element, prop, newValue ) {
        if ( element[ prop ] !== newValue ) element[ prop ] = newValue;
    }

    function coerceCheckboxValue( element, value ) {
        // The truthy wire value comes from the checkbox's own
        // ``value`` attribute (server-rendered), so each domain's
        // vocabulary lives in templates rather than duplicated here.
        // Browsers default unset checkbox ``value`` to ``'on'``,
        // which is exactly what ON_OFF needs; OPEN_CLOSE templates
        // set ``value="open"``. ``true`` / ``1`` are accepted as
        // universal truthy strings.
        if ( typeof value === 'boolean' ) return value;
        if ( typeof value === 'number' ) return value !== 0;
        if ( typeof value === 'string' ) {
            const lowered = value.toLowerCase();
            const truthy = ( element.value || 'on' ).toLowerCase();
            if ( lowered === truthy ) return true;
            return lowered === 'true' || lowered === '1';
        }
        return Boolean( value );
    }

    function syncSliderDisplay( slider ) {
        // Mirror a slider's current value into a paired display
        // element. Sliders opt in by declaring two data attributes
        // on the ``<input type=range>``:
        //   Hi.CONTROLLER_DISPLAY_TARGET_ATTR  CSS selector for the
        //       display element, looked up within the enclosing
        //       form.
        //   Hi.CONTROLLER_DISPLAY_FORMAT_ATTR  Format string with
        //       ``{n}`` as the value placeholder, e.g. ``{n}%``,
        //       ``{n}°``. Optional; defaults to ``{n}``.
        const selector = slider.getAttribute( Hi.CONTROLLER_DISPLAY_TARGET_ATTR );
        if ( ! selector ) return;
        const $display = $( slider ).closest( 'form' ).find( selector );
        if ( ! $display.length ) return;
        const format = slider.getAttribute( Hi.CONTROLLER_DISPLAY_FORMAT_ATTR ) || '{n}';
        $display.text( format.replace( '{n}', slider.value ) );
    }

    jQuery(function($) {
        // Slider drag mirror — keep the paired display in lock-step
        // with the thumb during user drag. ``input`` fires
        // continuously; ``change`` only fires on release, which
        // would let the displayed value lag behind the thumb.
        $( 'body' ).on(
            'input',
            `input[type=range][${Hi.CONTROLLER_DISPLAY_TARGET_ATTR}]`,
            function() { syncSliderDisplay( this ); }
        );

        // Track active drag so polling-driven value updates can
        // skip sliders the operator is currently manipulating.
        // Release-side handlers live on ``document`` so a pointer
        // release outside the viewport still bubbles and clears
        // the flag — listening on body alone would leak the flag
        // if the user dragged the thumb past the page edge.
        $( 'body' ).on(
            'mousedown touchstart pointerdown',
            'input[type=range]',
            function() { activeSliders.add( this ); }
        );
        $( document ).on(
            'mouseup touchend touchcancel pointerup pointercancel change blur',
            'input[type=range]',
            function() { activeSliders.delete( this ); }
        );
    });

})();
