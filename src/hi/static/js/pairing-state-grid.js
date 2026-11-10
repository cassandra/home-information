// Pairing state grid: the Clear all / Select all toggle of the
// refine-states modal. DOM-only; the server sees the checkboxes on
// submit. Uses jQuery event delegation for the async-loaded modal.

$(document).ready(function() {

    var PairingStateGrid = {

        getCheckboxes: function( $grid ) {
            return $grid.find( 'input[type="checkbox"]' );
        },

        // The label names what a click will do: clear while anything
        // is checked, otherwise select all.
        syncToggleLabel: function( $grid ) {
            var $toggle = $grid.find( '.' + Hi.PAIRING_STATE_GRID_TOGGLE_CLASS );
            var anyChecked = this.getCheckboxes( $grid ).is( ':checked' );
            var labelAttr = ( anyChecked
                              ? Hi.PAIRING_STATE_GRID_CLEAR_LABEL_ATTR
                              : Hi.PAIRING_STATE_GRID_SELECT_LABEL_ATTR );
            $toggle.text( $toggle.attr( labelAttr ));
        },

        toggleAll: function( $grid ) {
            var $checkboxes = this.getCheckboxes( $grid );
            $checkboxes.prop( 'checked', ! $checkboxes.is( ':checked' ));
            this.syncToggleLabel( $grid );
        }
    };

    $('body').on( 'click', '.' + Hi.PAIRING_STATE_GRID_TOGGLE_CLASS, function() {
        PairingStateGrid.toggleAll( $(this).closest( '.' + Hi.PAIRING_STATE_GRID_CLASS ));
    });

    $('body').on( 'change', '.' + Hi.PAIRING_STATE_GRID_CLASS + ' input[type="checkbox"]', function() {
        PairingStateGrid.syncToggleLabel( $(this).closest( '.' + Hi.PAIRING_STATE_GRID_CLASS ));
    });
});
