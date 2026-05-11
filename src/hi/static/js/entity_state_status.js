/*
 * Home Information - Entity-state status updates
 *
 * Consumes the ``entityStateStatusMap`` from the polling response
 * and applies per-EntityState UI updates. Each map entry is keyed
 * by CSS class and may carry:
 *
 *   attributes      DOM attributes to set on every matching element
 *                   (status, stroke, fill, etc.).
 *   controller      Controller widget state ({value, ...}) for the
 *                   matching elements; absent for sensor-only states.
 *   display_value   Display strings for the sensor card.
 */
(function() {
    'use strict';

    window.Hi = window.Hi || {};
    Hi.entityStateStatus = Hi.entityStateStatus || {};

    Hi.entityStateStatus.apply = function( statusMap ) {
        if ( ! statusMap ) return;
        const controllerSubMap = {};
        for ( const cssClass in statusMap ) {
            const entry = statusMap[ cssClass ];
            if ( entry.attributes ) {
                _applyAttributes( cssClass, entry.attributes );
            }
            if ( entry.display_value ) {
                _applyDisplay( cssClass, entry.display_value );
            }
            if ( entry.controller ) {
                controllerSubMap[ cssClass ] = entry.controller;
            }
        }
        Hi.controllers.applyValueMap( controllerSubMap );
    };

    function _applyAttributes( cssClass, attrMap ) {
        // When a matched element does not carry the named
        // attribute directly, the ``status`` attribute is
        // forwarded to descendent ``div[status]`` elements so CSS
        // selectors keyed on ``[status="..."]`` match through the
        // wrapper. Other attribute names are silently ignored on
        // that element.
        const elements = $( '.' + cssClass );
        for ( const attrName in attrMap ) {
            const attrValue = attrMap[ attrName ];
            elements.each( function() {
                if ( this.hasAttribute( attrName ) ) {
                    const currentValue = $( this ).attr( attrName );
                    if ( attrValue != null && ( currentValue !== String( attrValue ) ) ) {
                        $( this ).attr( attrName, attrValue );
                    }
                } else if ( attrName == 'status' ) {
                    $( this ).find( 'div[status]' ).attr( attrName, attrValue );
                }
            });
        }
    }

    function _applyDisplay( cssClass, displayValue ) {
        // Templates opt in to display refresh by tagging the
        // target element with one of ``display-text``,
        // ``display-magnitude``, ``display-unit``. The attribute
        // is presence-only; the polled ``display_value`` field of
        // the same name supplies the text. Fields absent on the
        // server side (e.g., ``magnitude`` for unit-less states)
        // leave the target element's existing text untouched.
        const $scope = $( '.' + cssClass );
        _setTextWhereAttr( $scope, 'display-text', displayValue.text );
        _setTextWhereAttr( $scope, 'display-magnitude', displayValue.magnitude );
        _setTextWhereAttr( $scope, 'display-unit', displayValue.unit_symbol );
    }

    function _setTextWhereAttr( $scope, attrName, text ) {
        if ( text == null ) return;
        const selector = '[' + attrName + ']';
        $scope.find( selector ).addBack( selector ).each( function() {
            if ( $( this ).text() !== text ) {
                $( this ).text( text );
            }
        });
    }

})();
