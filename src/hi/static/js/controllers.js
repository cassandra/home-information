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
                if ( element.classList.contains( 'brightness-slider' ) ) {
                    _syncBrightnessDisplay( element );
                }
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

    function _syncBrightnessDisplay( slider ) {
        // Mirror the slider's current value into the sibling
        // ``.brightness-value`` span as ``N%``. Called whenever
        // the slider's value changes (drag, button click,
        // controller-value polling) so the displayed percentage
        // stays in lock-step with the thumb position.
        const $display = $( slider ).closest( '.brightness-control' )
              .find( '.brightness-value' );
        if ( $display.length ) {
            $display.text( slider.value + '%' );
        }
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
            _syncBrightnessDisplay( $slider[ 0 ] );
        });

        // Mirror the value into the display span as the operator
        // drags the slider. ``input`` fires continuously during a
        // drag; ``change`` only fires on release, which would let
        // the displayed percentage lag behind the thumb position.
        $('body').on('input', '.brightness-slider', function() {
            _syncBrightnessDisplay( this );
        });
    });

})();
