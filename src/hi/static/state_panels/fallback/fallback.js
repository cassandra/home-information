/*
 * Fallback EntityStatusPanel — client-side behaviors specific to
 * the flat-list rendering used when no per-EntityType panel is
 * registered.
 *
 * Registered like any other panel JS. Adds two behaviors the
 * legacy flat-list controller templates depend on:
 *
 *   1. Checkbox status-text mirror. The flat-list on-off / open-close
 *      controller templates wrap a checkbox in a ``.on-off-control``
 *      container with a sibling ``.status-text`` caption. When the
 *      checkbox's checked state changes via polling, the caption
 *      mirror updates the text from the checkbox's
 *      ``data-on-text`` / ``data-off-text`` attributes. Opt-in
 *      via those attributes and the ``.on-off-control`` /
 *      ``.status-text`` container/sibling pair.
 *
 *   2. Continuous-slider preset buttons (e.g., the dimmer's Off /
 *      Full convenience buttons). The button's ``data-value`` is
 *      written into the sibling slider and ``change`` is fired so
 *      antinode's ``onchange-async`` handler submits the form —
 *      identical round-trip to the user dragging the slider.
 */
(function() {
    'use strict';

    function syncCheckboxStatusText( checkbox ) {
        const onText = checkbox.getAttribute( 'data-on-text' );
        const offText = checkbox.getAttribute( 'data-off-text' );
        if ( ! onText || ! offText ) return;
        const $statusText = $( checkbox ).closest( '.on-off-control' )
              .find( '.status-text' );
        if ( ! $statusText.length ) return;
        $statusText.text( checkbox.checked ? onText : offText );
    }

    // Registers with the framework's post-apply hook so the caption
    // mirror runs after the universal dispatcher has already updated
    // each checkbox's ``.checked`` state.
    if ( window.Hi && Hi.statePanels && typeof Hi.statePanels.registerUpdate === 'function' ) {
        Hi.statePanels.registerUpdate( function( statusMap ) {
            for ( const stateId in statusMap ) {
                $( `[data-state-id="${stateId}"][type="checkbox"]` ).each( function() {
                    syncCheckboxStatusText( this );
                });
            }
        });
    }

    jQuery( function( $ ) {
        // Continuous-slider preset buttons — write the
        // ``data-value`` into the sibling slider and fire change
        // for the antinode form submission.
        $( 'body' ).on(
            'click',
            `.${Hi.CONTROLLER_PRESET_BTN_CLASS}`,
            function() {
                const $btn = $( this );
                const $slider = $btn.closest( `.${Hi.CONTROLLER_SLIDER_CONTROL_CLASS}` )
                      .find( `.${Hi.CONTROLLER_SLIDER_CLASS}` );
                $slider.val( $btn.attr( Hi.DATA_VALUE_ATTR ) ).trigger( 'change' );
            }
        );
    });

})();
