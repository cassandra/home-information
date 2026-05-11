/*
 * Home Information - Controller widget interaction
 *
 * Two responsibilities:
 *
 *   1. Wire UI affordances on controller templates that need
 *      behavior beyond what antinode's onchange-async handler
 *      provides (e.g., the dimmer's Off / Full convenience
 *      buttons that drive the brightness slider).
 *
 *   2. Apply server-pushed controller widget state via
 *      ``Hi.controllers.applyValueMap``. Each map entry is keyed
 *      by CSS class and carries a controller-state dict
 *      ({value, ...}); every element matching the class gets its
 *      widget property updated (slider ``.value``, checkbox
 *      ``.checked``, ``<select>`` ``.value``, etc.).
 */
(function() {
    'use strict';

    window.Hi = window.Hi || {};
    Hi.controllers = Hi.controllers || {};

    // Sliders the user is actively dragging. Polling-driven value
    // updates skip these elements so a server refresh mid-drag
    // doesn't yank the thumb out from under the operator's
    // fingers. Cleared on pointerup / change so subsequent polls
    // resume normally — by definition the change-async submit on
    // release will reconcile the value at that point.
    const _activeSliders = new WeakSet();

    /**
     * Apply a class-name → controller-state map by finding each
     * matching element and updating the appropriate widget
     * property. Only applies updates when the new value differs
     * from the widget's current state — avoids interfering with
     * an in-progress user interaction (e.g., a slider mid-drag
     * whose optimistic update already matches the polled value).
     *
     * @param {Object} controllerMap - { className: { value, ... } }
     */
    Hi.controllers.applyValueMap = function( controllerMap ) {
        if ( !controllerMap ) return;
        Object.entries( controllerMap ).forEach( function( [ cssClass, controllerDict ] ) {
            const value = controllerDict.value;
            const $elements = $( '.' + cssClass );
            $elements.each( function() {
                _applyValueToElement( this, value );
            });
        });
    };

    function _applyValueToElement( element, value ) {
        const tag = element.tagName;
        if ( tag === 'INPUT' ) {
            const type = element.type;
            if ( type === 'range' || type === 'number' || type === 'text' ) {
                if ( type === 'range' && _activeSliders.has( element ) ) {
                    return;
                }
                _setIfDifferent( element, 'value', String( value ) );
                _syncSliderDisplay( element );
                return;
            }
            if ( type === 'checkbox' ) {
                const checked = _coerceCheckboxValue( element, value );
                if ( element.checked !== checked ) {
                    element.checked = checked;
                }
                _syncCheckboxStatusText( element, checked );
                return;
            }
        }
        if ( tag === 'SELECT' ) {
            _setIfDifferent( element, 'value', String( value ) );
            return;
        }
        // Other shapes (color picker, etc.) get their own branches
        // here as widgets are added. Silently no-op so unrelated
        // class-targeted elements (e.g., the wrapper div sharing
        // the same class for CSS purposes) are unaffected.
    }

    function _syncSliderDisplay( slider ) {
        // Mirror a slider's current value into a paired display
        // element. Sliders opt in by declaring two data
        // attributes on the ``<input type=range>``:
        //
        //   Hi.CONTROLLER_DISPLAY_TARGET_ATTR  CSS selector for
        //       the display element, looked up within the
        //       enclosing form.
        //   Hi.CONTROLLER_DISPLAY_FORMAT_ATTR  Format string with
        //       ``{n}`` as the value placeholder, e.g. ``{n}%``,
        //       ``{n}°``, ``{n}K``. Optional; defaults to ``{n}``.
        //
        // Attribute names are defined in DIVID (server) and
        // mirrored in main.js (client) — templates emit them via
        // the DIVID entries and this code reads them via Hi.
        //
        // Called whenever the slider's value changes (drag,
        // button click, controller-value polling) so the
        // displayed value stays in lock-step with the thumb.
        const selector = slider.getAttribute( Hi.CONTROLLER_DISPLAY_TARGET_ATTR );
        if ( ! selector ) return;
        const $display = $( slider ).closest( 'form' ).find( selector );
        if ( ! $display.length ) return;
        const format = slider.getAttribute( Hi.CONTROLLER_DISPLAY_FORMAT_ATTR ) || '{n}';
        $display.text( format.replace( '{n}', slider.value ) );
    }

    function _syncCheckboxStatusText( checkbox, checked ) {
        // Mirror a checkbox's checked-state into a paired text
        // label (e.g., the "On"/"Off" caption under a toggle).
        // Labels are carried as ``data-on-text`` and
        // ``data-off-text`` on the checkbox so different
        // controller variants can use domain-specific wording
        // (e.g., "Open"/"Closed", "Locked"/"Unlocked"). The
        // status text lives in a sibling ``.status-text`` within
        // the enclosing ``.on-off-control`` container — opt-in:
        // checkboxes without the data attributes or container
        // are silently skipped so unrelated checkboxes are
        // unaffected.
        const onText = checkbox.getAttribute( 'data-on-text' );
        const offText = checkbox.getAttribute( 'data-off-text' );
        if ( ! onText || ! offText ) return;
        const $statusText = $( checkbox ).closest( '.on-off-control' )
              .find( '.status-text' );
        if ( ! $statusText.length ) return;
        $statusText.text( checked ? onText : offText );
    }

    function _setIfDifferent( element, prop, newValue ) {
        if ( element[ prop ] !== newValue ) {
            element[ prop ] = newValue;
        }
    }

    function _coerceCheckboxValue( element, value ) {
        // The truthy wire value comes from the checkbox's own
        // ``value`` attribute (server-rendered), so each domain's
        // vocabulary lives in templates rather than duplicated
        // here. Browsers default unset checkbox ``value`` to
        // ``'on'``, which is exactly what ON_OFF needs;
        // OPEN_CLOSE templates set ``value="open"``. ``true`` /
        // ``1`` remain accepted as universal truthy strings.
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

    jQuery(function($) {
        // Continuous-slider preset buttons (e.g., the dimmer's
        // Off/Full). The button's ``data-value`` is written to
        // the sibling slider and ``change`` is triggered so
        // antinode's ``onchange-async`` handler submits the form
        // — identical round-trip to dragging the slider.
        $('body').on(
            'click',
            `.${Hi.CONTROLLER_PRESET_BTN_CLASS}`,
            function() {
                const $btn = $(this);
                const $slider = $btn.closest( `.${Hi.CONTROLLER_SLIDER_CONTROL_CLASS}` )
                      .find( `.${Hi.CONTROLLER_SLIDER_CLASS}` );
                $slider.val( $btn.attr( Hi.DATA_VALUE_ATTR ) ).trigger( 'change' );
                _syncSliderDisplay( $slider[ 0 ] );
            }
        );

        // Mirror the value into the display element as the
        // operator drags any slider that opted in. ``input``
        // fires continuously during a drag; ``change`` only
        // fires on release, which would let the displayed value
        // lag behind the thumb position.
        $('body').on(
            'input',
            `input[type=range][${Hi.CONTROLLER_DISPLAY_TARGET_ATTR}]`,
            function() {
                _syncSliderDisplay( this );
            }
        );

        // Track active drag so polling-driven value updates can
        // skip sliders the operator is currently manipulating.
        // Set on pointer-down (mouse / touch / pen via Pointer
        // Events). Cleared on pointer release and on ``change``
        // (the canonical "value committed" signal — covers
        // keyboard arrow adjustments too).
        //
        // Release-side handlers live on ``document``, not ``body``:
        // a pointer release that happens off the slider element
        // (or even outside the viewport) still bubbles to document,
        // ensuring the flag clears so subsequent polls can resume
        // updating. Listening on body alone would leak the flag if
        // the user dragged the thumb past the page edge before
        // releasing.
        $('body').on(
            'mousedown touchstart pointerdown',
            'input[type=range]',
            function() { _activeSliders.add( this ); }
        );
        $(document).on(
            'mouseup touchend touchcancel pointerup pointercancel change blur',
            'input[type=range]',
            function() { _activeSliders.delete( this ); }
        );
    });

})();
