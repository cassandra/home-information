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
 *   2. Apply server-pushed controller values to widgets via
 *      ``Hi.controllers.applyValueMap`` — called by the polling
 *      layer with the ``cssControllerValueMap`` from the status
 *      response. Each map entry is a class-name → value pair;
 *      every element matching the class gets its widget property
 *      updated (slider ``.value``, checkbox ``.checked``,
 *      ``<select>`` ``.value``, etc.).
 *
 * The controller-value path is parallel to the existing CSS-class
 * status path (status drives icon styling via attributes; values
 * drive interactive widget state via DOM properties). Replaces
 * the older checkbox+select special-cases that were inlined in
 * status.js's CSS-class-update handler.
 */
(function() {
    'use strict';

    window.Hi = window.Hi || {};
    Hi.controllers = Hi.controllers || {};

    /**
     * Apply a class-name → controller-value map by finding each
     * matching element and updating the appropriate widget
     * property. Only applies updates when the new value differs
     * from the widget's current state — avoids interfering with
     * an in-progress user interaction (e.g., a slider mid-drag
     * whose optimistic update already matches the polled value).
     *
     * @param {Object} controllerValueMap - { className: value }
     */
    Hi.controllers.applyValueMap = function( controllerValueMap ) {
        if ( !controllerValueMap ) return;
        Object.entries( controllerValueMap ).forEach( function( [ cssClass, value ] ) {
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
                _setIfDifferent( element, 'value', String( value ) );
                _syncSliderDisplay( element );
                return;
            }
            if ( type === 'checkbox' ) {
                const checked = _coerceCheckboxValue( value );
                if ( element.checked !== checked ) {
                    element.checked = checked;
                }
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

    function _setIfDifferent( element, prop, newValue ) {
        if ( element[ prop ] !== newValue ) {
            element[ prop ] = newValue;
        }
    }

    function _coerceCheckboxValue( value ) {
        if ( typeof value === 'boolean' ) return value;
        if ( typeof value === 'number' ) return value !== 0;
        if ( typeof value === 'string' ) {
            const lowered = value.toLowerCase();
            return lowered === 'on' || lowered === 'true' || lowered === '1';
        }
        return Boolean( value );
    }

    jQuery(function($) {
        // Dimmer Off / Full buttons (controller_light_dimmer.html).
        // Find the sibling slider, set its value to the button's
        // ``data-value``, and trigger ``change`` so antinode's
        // ``onchange-async`` handler submits the parent form —
        // identical round-trip to dragging the slider.
        $('body').on('click', '.brightness-btn', function() {
            const $btn = $(this);
            const $slider = $btn.closest('.brightness-control')
                  .find('.brightness-slider');
            $slider.val( $btn.data('value') ).trigger('change');
            _syncSliderDisplay( $slider[ 0 ] );
        });

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
    });

})();
