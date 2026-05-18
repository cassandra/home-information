/*
 * EntityStatePanel JS — thermostat.
 *
 * The dial's setpoint marker and current-temperature marker need
 * SVG rotations computed from the numeric temperature magnitude.
 * CSS keyed on the ``status`` attribute can't compute angles, so
 * this panel registers a polling handler with the framework: the
 * handler runs after each polling apply pass and re-positions the
 * markers based on the latest values delivered in the statusMap.
 *
 * Each marker carries its own ``data-marker-state-id`` attribute
 * naming the EntityState whose magnitude drives its angle. This is
 * a panel-private attribute (distinct from the framework's
 * ``data-state-id``) so the universal dispatcher doesn't try to
 * apply text/attr updates to the SVG marker group — those updates
 * are inappropriate here. The handler looks up the entry directly
 * by state id, so the dispatch works uniformly across the modal /
 * list / grid render contexts even though their non-dial layouts
 * differ.
 *
 * Initial positioning on page load uses ``data-temp-value`` baked
 * in by the server-rendered template so the dial reads correctly
 * before the first polling refresh. The template seeds this from
 * the user's display-unit magnitude, matching the polling-time
 * unit so the dial calibration is consistent across both paths.
 */
(function() {
    'use strict';

    // Temperature range that maps to the dial's visible arc.
    // 50°F at -135° (lower-left) → 90°F at +135° (lower-right);
    // bottom 90° is the dial's "gap" and not part of the range.
    const TEMP_RANGE_LOW = 50;
    const TEMP_RANGE_HIGH = 90;
    const ANGLE_LOW = -135;
    const ANGLE_HIGH = 135;

    const MARKER_SELECTOR = '.dial-setpoint-marker, .dial-current-marker';

    function temperatureToAngle( tempValue ) {
        const value = parseFloat( tempValue );
        if ( isNaN( value ) ) return 0;
        const clamped = Math.max( TEMP_RANGE_LOW, Math.min( TEMP_RANGE_HIGH, value ) );
        const fraction = ( clamped - TEMP_RANGE_LOW ) / ( TEMP_RANGE_HIGH - TEMP_RANGE_LOW );
        return ANGLE_LOW + fraction * ( ANGLE_HIGH - ANGLE_LOW );
    }

    function applyAngleToMarker( $marker, tempValue ) {
        // Hide the marker when there is no numeric value yet (empty
        // ``data-temp-value`` from a sensor with no reading); otherwise
        // ``temperatureToAngle`` would clamp NaN to 0 and the marker
        // would settle at the dial's top, misleadingly.
        const value = parseFloat( tempValue );
        if ( isNaN( value ) ) {
            $marker.css( 'display', 'none' );
            return;
        }
        $marker.css( 'display', '' );
        $marker.attr( 'transform', 'rotate(' + temperatureToAngle( value ) + ' 110 110)' );
    }

    // Initial render: each marker has the numeric value baked in
    // as ``data-temp-value``. Position them from those values so
    // the dial reads correctly before the first polling cycle.
    function applyInitialMarkerAngles() {
        $( '.hi-state-panel-thermostat' ).find( MARKER_SELECTOR ).each( function() {
            applyAngleToMarker( $( this ), $( this ).attr( 'data-temp-value' ) );
        });
    }

    // Polling-driven updates: each marker self-identifies via
    // ``data-marker-state-id`` — the EntityState whose magnitude
    // drives its angle. Look up that state id in the statusMap
    // and refresh both the cached ``data-temp-value`` and the
    // rotation.
    function applyMarkerAnglesFromStatusMap( statusMap ) {
        $( '.hi-state-panel-thermostat' ).find( MARKER_SELECTOR ).each( function() {
            const $marker = $( this );
            const stateId = $marker.attr( 'data-marker-state-id' );
            if ( ! stateId ) return;
            const entry = statusMap[ stateId ];
            if ( ! entry || ! entry.display ) return;
            const magnitude = entry.display.magnitude;
            if ( magnitude == null ) return;
            $marker.attr( 'data-temp-value', magnitude );
            applyAngleToMarker( $marker, magnitude );
        });
    }

    // Keep ``data-hvac-mode`` on each thermostat panel synced with the
    // polled HVAC_MODE value, so CSS rules on the panel root can
    // switch between single and dual setpoint UI (markers + control
    // rows + summary text) when the user changes the mode.
    function applyHvacModeFromStatusMap( statusMap ) {
        $( '.hi-state-panel-thermostat[data-hvac-mode-state-id]' ).each( function() {
            const $panel = $( this );
            const stateId = $panel.attr( 'data-hvac-mode-state-id' );
            const entry = statusMap[ stateId ];
            if ( ! entry ) return;
            // Mode controllers expose their value via entry.controller.value;
            // some integrations may surface it via the display text instead.
            let value = null;
            if ( entry.controller && entry.controller.value != null ) {
                value = entry.controller.value;
            } else if ( entry.display && entry.display.text ) {
                value = entry.display.text.toLowerCase();
            }
            if ( value == null ) return;
            $panel.attr( 'data-hvac-mode', String( value ).toLowerCase() );
        });
    }

    if ( window.Hi && Hi.statePanels ) {
        if ( typeof Hi.statePanels.registerUpdate === 'function' ) {
            Hi.statePanels.registerUpdate( applyMarkerAnglesFromStatusMap );
            Hi.statePanels.registerUpdate( applyHvacModeFromStatusMap );
        }
        if ( typeof Hi.statePanels.registerInit === 'function' ) {
            // Fires on initial page load and after each async fragment
            // insert, so dial markers in dynamically-loaded modals get
            // their angles set from server-rendered ``data-temp-value``
            // before the first polling tick.
            Hi.statePanels.registerInit( applyInitialMarkerAngles );
        }
    }

    // Helper: POST the controller form's value to its action URL
    // without engaging antinode's form-submit machinery (which would
    // try to replace the rendered widget with the server response
    // and produce the wrong shape for the thermostat's custom UI).
    // The unified ``Hi.entityStateStatus.apply`` path handles the UI
    // side; polling reconciles on the next tick.
    function postControllerChange( $form, value ) {
        const url = $form.attr( 'action' );
        const csrf = $form.find( 'input[name="csrfmiddlewaretoken"]' ).val();
        $.ajaxSuppressLoader = true;
        return $.post( url, {
            csrfmiddlewaretoken: csrf,
            value: value,
        }).always( function() {
            $.ajaxSuppressLoader = false;
        });
    }

    // Mode / Fan / Preset selects: plain selects with no antinode
    // hooks. The framework's unified change-listener has already
    // synthesized the status update and applied the optimistic UI
    // (including the panel-root ``data-hvac-mode`` that swaps single
    // vs dual setpoint visibility); we just push the value to the
    // server.
    $( document ).on( 'change', '.hi-state-panel-thermostat .thermostat-select', function() {
        const $select = $( this );
        const $form = $select.closest( 'form.thermostat-select-form' );
        if ( ! $form.length ) return;
        postControllerChange( $form, $select.val() );
    });

    // Setpoint stepper: bump the hidden value and let the framework's
    // unified status-apply path handle the UI (display text, dial
    // marker re-positioning, etc.). Trigger ``change`` on the input so
    // the generic optimistic-apply handler picks it up. Server POST
    // runs in parallel; polling reconciles on the next tick.
    $( document ).on( 'click', '.hi-state-panel-thermostat .stepper-btn', function( e ) {
        e.preventDefault();
        const $btn = $( this );
        const $stepper = $btn.closest( '.setpoint-stepper' );
        const $form = $stepper.find( 'form.setpoint-stepper-form' );
        if ( ! $form.length ) return;
        const $input = $form.find( 'input.setpoint-stepper-input' );
        const cur = parseFloat( $input.val() );
        const delta = parseFloat( $btn.attr( 'data-stepper-delta' ) ) || 0;
        if ( isNaN( cur ) || ! delta ) return;
        const next = cur + delta;
        $input.val( next ).trigger( 'change' );
        postControllerChange( $form, next );
    });

})();
