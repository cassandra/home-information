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

    if ( window.Hi && Hi.statePanels ) {
        if ( typeof Hi.statePanels.registerUpdate === 'function' ) {
            Hi.statePanels.registerUpdate( applyMarkerAnglesFromStatusMap );
        }
        if ( typeof Hi.statePanels.registerInit === 'function' ) {
            // Fires on initial page load and after each async fragment
            // insert, so dial markers in dynamically-loaded modals get
            // their angles set from server-rendered ``data-temp-value``
            // before the first polling tick.
            Hi.statePanels.registerInit( applyInitialMarkerAngles );
        }
    }

})();
