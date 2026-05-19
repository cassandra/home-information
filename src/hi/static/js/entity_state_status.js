/*
 * Home Information — Entity-state polling-update dispatcher.
 *
 * Consumes the ``entityStateStatusMap`` from the polling response
 * and applies per-EntityState DOM updates. The map is keyed by the
 * EntityState id (as a string); each entry may carry a status
 * value, a controller value, a display projection, and an SVG
 * style bundle.
 *
 * Element-level contract: every DOM element that wants polling
 * updates carries ``data-state-id="<entity_state_id>"`` plus one or
 * more declaration attributes. Each declaration is presence-only:
 *
 *   data-status            → set the element's ``status`` attr to
 *                            ``entry.status`` (singular status push;
 *                            CSS rules elsewhere react to it).
 *   data-controller-value  → set the form value / checked / selected
 *                            from ``entry.controller.value``.
 *   data-display-text      → set element text to ``entry.display.text``.
 *   data-display-magnitude → set element text to ``entry.display.magnitude``.
 *   data-display-unit      → set element text to ``entry.display.unit``.
 *   data-svg-style         → set every attribute in ``entry.svg_style``
 *                            (status, stroke, fill, stroke-width,
 *                            fill-opacity, stroke-dasharray) on this
 *                            element. Used by LocationView SVG icon /
 *                            path elements.
 *
 * The dispatcher walks ``[data-state-id]`` once, looks up the
 * entry, and applies each declaration the element opts into. No
 * descendant traversal and no class-based join — each element is
 * self-describing, so authors place the markers on whichever
 * element they want updated.
 *
 * After the universal apply pass, registered EntityStatePanel
 * handlers run. Panels that need behavior beyond what the universal
 * dispatcher handles (e.g., a thermostat dial whose SVG marker
 * angles are computed from numeric values) register a handler via
 * ``Hi.statePanels.registerUpdate``. The fallback flat-list rendering is
 * itself a panel; its panel JS registers a handler for the
 * flat-list-specific behaviors (checkbox status-text mirror, dimmer
 * preset buttons, etc.).
 */
(function() {
    'use strict';

    window.Hi = window.Hi || {};
    Hi.entityStateStatus = Hi.entityStateStatus || {};

    // EntityStatePanel JS that wants to react to polling updates
    // beyond what CSS keyed on the ``status`` attribute can do
    // registers an update handler via ``registerUpdate``. Update
    // handlers receive the full statusMap keyed by state id and
    // scope their own work using ``data-state-id`` on the elements
    // they manage. They run after the universal apply pass on each
    // polling tick.
    //
    // Panels that need a per-insertion init step (e.g., a thermostat
    // dial that has to position SVG markers from server-rendered
    // ``data-temp-value`` attributes before any polling tick) register
    // an init handler via ``registerInit``. Init handlers fire at
    // jQuery ready for the initial page render AND after every async
    // content insertion (via antinode), so panels in dynamically-loaded
    // modals get a chance to initialize before the first polling tick.
    // Init handlers must be idempotent — they re-scan the whole
    // document on each call and should be safe to invoke on already-
    // initialized elements.
    const panelUpdateHandlers = [];
    const panelInitHandlers = [];
    Hi.statePanels = Hi.statePanels || {
        registerUpdate: function( handler ) {
            if ( typeof handler === 'function' ) panelUpdateHandlers.push( handler );
        },
        registerInit: function( handler ) {
            if ( typeof handler === 'function' ) panelInitHandlers.push( handler );
        }
    };

    function runPanelInitHandlers() {
        for ( const handler of panelInitHandlers ) {
            try {
                handler();
            } catch ( e ) {
                console.error( 'EntityStatePanel init handler error:', e );
            }
        }
    }

    // Sliders the user is actively dragging. Polling-driven value
    // updates skip these elements so a server refresh mid-drag
    // doesn't yank the thumb out from under the operator's fingers.
    const activeSliders = new WeakSet();

    Hi.entityStateStatus.apply = function( statusMap ) {
        if ( ! statusMap ) return;
        $( '[data-state-id]' ).each( function() {
            const $el = $( this );
            const entry = statusMap[ $el.attr( 'data-state-id' ) ];
            if ( ! entry ) return;

            if ( entry.status != null && this.hasAttribute( 'data-status' ) ) {
                setAttrIfDifferent( this, 'status', entry.status );
            }
            if ( entry.svg_style && this.hasAttribute( 'data-svg-style' ) ) {
                for ( const attrName in entry.svg_style ) {
                    const attrValue = entry.svg_style[ attrName ];
                    if ( attrValue == null ) continue;
                    setAttrIfDifferent( this, attrName, attrValue );
                }
            }
            if ( entry.display ) {
                if ( entry.display.text != null
                     && this.hasAttribute( 'data-display-text' ) ) {
                    setTextIfDifferent( this, entry.display.text );
                }
                if ( entry.display.magnitude != null
                     && this.hasAttribute( 'data-display-magnitude' ) ) {
                    setTextIfDifferent( this, String( entry.display.magnitude ) );
                }
                if ( entry.display.unit != null
                     && this.hasAttribute( 'data-display-unit' ) ) {
                    setTextIfDifferent( this, entry.display.unit );
                }
            }
            if ( entry.controller
                 && this.hasAttribute( 'data-controller-value' ) ) {
                applyControllerValue( this, entry.controller.value );
            }
        });

        for ( const handler of panelUpdateHandlers ) {
            try {
                handler( statusMap );
            } catch ( e ) {
                console.error( 'EntityStatePanel handler error:', e );
            }
        }
    };

    function setAttrIfDifferent( element, attrName, attrValue ) {
        const newValue = String( attrValue );
        if ( element.getAttribute( attrName ) !== newValue ) {
            element.setAttribute( attrName, newValue );
        }
    }

    function setTextIfDifferent( element, text ) {
        if ( element.textContent !== text ) {
            element.textContent = text;
        }
    }

    function applyControllerValue( element, value ) {
        // Skip if the user currently has this control focused: prevents
        // poll updates from clobbering a value mid-edit on selects,
        // text/number inputs, and freshly-clicked checkboxes. Slider
        // drag does not always keep :focus, so the activeSliders
        // WeakSet still handles that case below.
        if ( element === document.activeElement ) return;
        const tag = element.tagName;
        if ( tag === 'INPUT' ) {
            const type = element.type;
            if ( type === 'range' || type === 'number' || type === 'text' ) {
                if ( type === 'range' && activeSliders.has( element ) ) return;
                setPropIfDifferent( element, 'value', String( value ) );
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
            setPropIfDifferent( element, 'value', String( value ) );
            return;
        }
        // Other shapes (color picker, etc.) get their own branches
        // here as widgets are added.
    }

    function setPropIfDifferent( element, prop, newValue ) {
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

    // Generic optimistic-apply for user-driven control changes. When
    // a state-bound control changes (select / checkbox / numeric
    // input / scripted change on a hidden input), synthesize a one-
    // entry statusMap and run the universal apply. Dependent display
    // elements (``data-display-text``, ``data-display-magnitude``,
    // ``data-status``, panel-root status attr, etc.) update in lock
    // step with the user's intent, and registered update handlers
    // (dial marker positioning, panel-root ``data-hvac-mode`` sync,
    // etc.) fire immediately — the polling cycle merely confirms or
    // corrects, never drives the first-frame UI response.
    //
    // The server-bound submit path (antinode's ``onchange-async``
    // form-submit) runs independently of this handler on the same
    // ``change`` event, so error responses still surface through the
    // normal mechanism. If the server rejects the change, the next
    // polling tick overwrites the optimistic value with the canonical
    // one.
    function buildSyntheticEntry( $el ) {
        const stateId = $el.attr( 'data-state-id' );
        const tag = ( $el.prop( 'tagName' ) || '' ).toUpperCase();
        const type = ( $el.attr( 'type' ) || '' ).toLowerCase();
        let value = $el.val();
        let displayText = String( value );

        if ( tag === 'SELECT' ) {
            const $opt = $el.find( 'option:selected' );
            if ( $opt.length ) displayText = $opt.text() || displayText;
        } else if ( tag === 'INPUT' && type === 'checkbox' ) {
            const checked = $el.prop( 'checked' );
            value = checked ? ( $el.val() || 'on' ) : 'off';
            displayText = checked
                ? ( $el.attr( 'data-on-text' ) || 'On' )
                : ( $el.attr( 'data-off-text' ) || 'Off' );
        } else if ( stateId ) {
            // Numeric / hidden-input case: format the optimistic value
            // by mirroring the existing displayed text — same decimal
            // precision and same unit suffix. Heuristic, but it keeps
            // an optimistic "73.0°F" matching the canonical "72.0°F"
            // until the next polling tick reconciles. Backend authority
            // returns on every poll, so a brief divergence here is
            // self-correcting; the goal is just to avoid the visible
            // jump that happens when the optimistic value is
            // unformatted ("73") and polling replaces it with the
            // formatted version ("73.0°F").
            const $paired = $( '[data-state-id="' + stateId + '"][data-display-text]' )
                  .not( $el ).first();
            if ( $paired.length ) {
                const prev = $paired.text();
                const numMatch = prev.match( /-?\d+\.?\d*/ );
                const decimalMatch = numMatch ? numMatch[ 0 ].match( /\.(\d+)$/ ) : null;
                const precision = decimalMatch ? decimalMatch[ 1 ].length : 0;
                const unitMatch = prev.match( /[^\d\s.\-+][^\d]*$/ );
                const unit = unitMatch ? unitMatch[ 0 ] : '';
                const num = parseFloat( value );
                if ( ! isNaN( num ) ) {
                    displayText = num.toFixed( precision ) + unit;
                }
            }
        }

        const entry = {
            controller: { value: value },
            display:    { text: displayText },
            status:     String( value ).toLowerCase(),
        };
        const magnitude = parseFloat( value );
        if ( ! isNaN( magnitude ) ) {
            entry.display.magnitude = magnitude;
        }
        return entry;
    }

    jQuery(function($) {
        $( document ).on(
            'change',
            '[data-state-id][data-controller-value]',
            function() {
                const $el = $( this );
                const stateId = $el.attr( 'data-state-id' );
                if ( ! stateId ) return;
                const entry = buildSyntheticEntry( $el );
                const synthetic = {};
                synthetic[ stateId ] = entry;
                Hi.entityStateStatus.apply( synthetic );
            }
        );

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

        // Initial pass for the first page render. Async-loaded
        // fragments piggyback on antinode's afterAsyncRender hook
        // (for HTML and set-attribute responses) and its dedicated
        // afterModalRender hook (for JSON-delivered modals, which
        // are inserted after afterAsyncRender fires).
        runPanelInitHandlers();
        if ( window.AN ) {
            if ( typeof window.AN.addAfterAsyncRenderFunction === 'function' ) {
                window.AN.addAfterAsyncRenderFunction( runPanelInitHandlers );
            }
            if ( typeof window.AN.addAfterModalRenderFunction === 'function' ) {
                window.AN.addAfterModalRenderFunction( runPanelInitHandlers );
            }
        }
    });

})();
