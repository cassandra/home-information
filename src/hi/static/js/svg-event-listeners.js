(function() {

    window.Hi = window.Hi || {};
    window.Hi.location = window.Hi.location || {};
    window.Hi.edit.icon = window.Hi.edit.icon || {};
    window.Hi.edit.path = window.Hi.edit.path || {};

    /* 
      SVG EVENT LISTENERS
      
      - Listeners and dispatching of events for location SVG interactions.
    */

    const SVG_TRANSFORM_ACTION_SCALE_KEY = 's';
    const SVG_TRANSFORM_ACTION_ROTATE_KEY = 'r';
    const SVG_TRANSFORM_ACTION_ZOOM_IN_KEY = '+';
    const SVG_TRANSFORM_ACTION_ZOOM_OUT_KEY = '-';

    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3; // Differentiate between move events and sloppy clicks
    const PIXEL_MOVE_DISTANCE_SCALE_FACTOR = 500.0;
    const ZOOM_SCALE_FACTOR_PERCENT = 10.0;

    const LOCATION_VIEW_EDIT_PANE_SELECTOR = '#hi-location-view-edit';
    const API_EDIT_LOCATION_VIEW_GEOMETRY_URL = '/location/edit/location-view/geometry';
    
    const SvgTransformType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };
    let gSvgTransformType = SvgTransformType.MOVE;

    let gSelectedLocationViewSvg = null;
    let gSvgTransformData = null;
    let gLastMousePosition = { x: 0, y: 0 };
    let gIgnoreCLick = false;  // Set by mouseup handling when no click handling should be done

    $(document).ready(function() {

	$(document).on('mousedown', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    let handled = Hi.edit.icon.handleMouseDown( event );
	    if ( ! handled ) {
		Hi.location.handleMouseDown( event );
	    }
	});
	$(document).on('mousemove', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    let handled = Hi.edit.icon.handleMouseMove( event );
	    if ( ! handled ) {
		Hi.location.handleMouseMove( event );
	    }
	});
	$(document).on('mouseup', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    let handled = Hi.edit.icon.handleMouseUp( event );
	    if ( ! handled ) {
		Hi.location.handleMouseUp( event );
	    }
	});
	$(document).on('wheel', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    let handled = Hi.edit.icon.handleMouseWheel( event );
	    if ( ! handled ) {
		Hi.location.handleMouseWheel( event );
	    }
	});
	$(document).on('click', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    let handled = Hi.edit.icon.handleClick( event );
	    if ( ! handled ) {
		Hi.edit.path.handleClick( event );
	    }
	    Hi.location.handleClick( event );
	});
	$(document).on('keydown', function(event) {
	    if ( $(event.target).is('input, textarea') ) {
		return;
	    }
	    if ($(event.target).closest('.modal').length > 0) {
		return;
	    }
	    let handled = Hi.edit.icon.handleKeyDown( event );
	    if ( ! handled ) {
		handled = Hi.edit.path.handleKeyDown( event );
	    }
	    if ( ! handled ) {
		Hi.location.handleKeyDown( event );
	    }
	});
    });
 
})();
