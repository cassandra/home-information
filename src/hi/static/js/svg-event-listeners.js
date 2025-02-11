(function() {

    window.Hi = window.Hi || {};
    window.Hi.location = window.Hi.location || {};
    window.Hi.edit.icon = window.Hi.edit.icon || {};
    window.Hi.edit.path = window.Hi.edit.path || {};

    /* 
      SVG EVENT LISTENERS
      
      - Listeners and dispatching of events for location SVG interactions.
    */

    const LAST_MOVE_THROTTLE_THRESHOLD_MS = 10;
    const POINTER_MOVE_THRESHOLD_PIXELS = 2;
    const POINTER_SCALE_THRESHOLD_PIXELS = 3;
    const POINTER_ROTATE_THRESHOLD_DEGREES = 3;

    const activePointers = new Map();
    const gLastMoveEventTimes = new Map();
    let gCurrentEventData = null;
	
    class PointerEventData {
	constructor( startEvent, startDistance = 0, startAngle = 0 ) {
            this.start = {
		event: startEvent,
		x: startEvent.clientX,
		y: startEvent.clientY,
		distance: startDistance,
		angle: startAngle,
            };
	    
            this.previous = { ...this.start };
            this.last = { ...this.start };
	}
	get deltaX() {
            return this.last.x - this.start.x;
	}
	get deltaY() {
            return this.last.y - this.start.y;
	}
	get deltaDistanceStart() {
            return this.last.distance - this.start.distance;
	}
	get deltaDistancePrevious() {
            return this.last.distance - this.previous.distance;
	}
	get deltaAngleStart() {
            return this.last.angle - this.start.angle;
	}
	get deltaAnglePrevious() {
            return this.last.angle - this.previous.angle;
	}
	update( lastEvent, distance = null, angle = null ) {

	    this.previous = { ...this.last };
	    this.last.event = lastEvent;
            this.last.x = lastEvent.clientX;
            this.last.y = lastEvent.clientY;

            if ( distance !== null ) this.last.distance = distance;
            if ( angle !== null ) this.last.angle = angle;
	}
    }

    function getDistance( p1, p2 ) {
	let dx = p1.x - p2.x;
	let dy = p1.y - p2.y;
	return Math.sqrt( dx * dx + dy * dy );
    }
    function getAngle( p1, p2 ) {
	return Math.atan2( p2.y - p1.y, p2.x - p1.x ) * ( 180 / Math.PI );
    }

    function addPointerListener( eventType, selector, handler, passive = true ) {
	// N.B.
	//   - "passive = false" ensures preventDefault() works for pointer events.
	//   - jQuery doesn't support this option, so cannot use its event registrations for these
	
        $(document).each( function() {
	    this.addEventListener( eventType, function( event ) {
                if ( event.target.closest( selector )) {
		    handler( event );
                }
	    }, { passive: passive });
        });
    }

    function handlePointerDownEvent( event ) {

	activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );

	let handled = false;
	if ( activePointers.size === 1 ) {
	    gCurrentEventData = new PointerEventData( event );
	    handled = Hi.edit.icon.handlePointerDown( gCurrentEventData );
            if ( ! handled) {
		handled = Hi.location.handlePointerDown( gCurrentEventData );
	    }
	    
	} else if ( activePointers.size === 2 ) {
	    let points = Array.from( activePointers.values() );
	    const distance = getDistance( points[0], points[1] );
	    const angle = getAngle( points[0], points[1] );
	    gCurrentEventData = new PointerEventData( event, distance, angle );

	    handled = Hi.edit.icon.scaleAndRotateFromPointerEvents( gCurrentEventData );
	    if ( ! handled) {
		handled = Hi.location.scaleAndRotateFromPointerEvents( gCurrentEventData );
	    }
	}
	
	if ( handled ) {
	    event.preventDefault();
	    event.stopImmediatePropagation();
   	}
	event.target.setPointerCapture( event.pointerId );
    }

    function handlePointerMoveEvent( event ) {
	if ( ! gCurrentEventData ) { return; }

	// Guarding against event floods and performance issues.
	let now = Date.now();
	if ( gLastMoveEventTimes.has( event.pointerId )) {
	    const deltaTimeMs = now - gLastMoveEventTimes.get( event.pointerId );
	    if ( deltaTimeMs < LAST_MOVE_THROTTLE_THRESHOLD_MS ) {
		return;
	    }
	    gLastMoveEventTimes.set( event.pointerId, now );
	}
	
	let lastPointer = activePointers.get( event.pointerId );
	if ( lastPointer ) {    

            let last_pointer_delta_x = event.clientX - lastPointer.x;
            let last_pointer_delta_y = event.clientY - lastPointer.y;

	    // Ignore micro-movements to avoid re-render floods and performance issues.
            if (( Math.abs( last_pointer_delta_x ) < POINTER_MOVE_THRESHOLD_PIXELS )
		&& ( Math.abs( last_pointer_delta_y ) < POINTER_MOVE_THRESHOLD_PIXELS )) {
		return;
            }

	    activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );

	    let handled = false;
	    if ( activePointers.size === 1 ) {
		gCurrentEventData.update( event );

		handled = Hi.edit.icon.handlePointerMove( gCurrentEventData );
		if ( ! handled) {
		    handled = Hi.location.handlePointerMove( gCurrentEventData );
		}
		
	    } else if ( activePointers.size === 2 ) {

		let points = Array.from( activePointers.values() );
		const distance = getDistance( points[0], points[1] );
		const angle = getAngle( points[0], points[1] );

		gCurrentEventData.update( event, distance, angle );

		handled = Hi.edit.icon.scaleAndRotateFromPointerEvents( gCurrentEventData );
		if ( ! handled) {
		    handled = Hi.location.scaleAndRotateFromPointerEvents( gCurrentEventData );
		}
	    }
	    if ( handled ) {
		event.preventDefault();
		event.stopImmediatePropagation();
   	    }
	}
    }

    function handlePointerUpEvent( event ) {
	if ( ! gCurrentEventData ) { return; }

	const initialActivePointers = activePointers.size;
	let lastPointer = activePointers.get( event.pointerId );
	if ( lastPointer ) {    
	    activePointers.delete( event.pointerId );

	    gCurrentEventData.update( event );
	    let handled = false;
	    if ( initialActivePointers == 2 ) {
		handled = Hi.edit.icon.scaleAndRotateFromPointerEvents( gCurrentEventData );
		if ( ! handled) {
		    handled = Hi.location.scaleAndRotateFromPointerEvents( gCurrentEventData );
		}
	    } else {
		handled = Hi.edit.icon.handlePointerUp( gCurrentEventData );
		if ( ! handled) {
		    handled = Hi.location.handlePointerUp( gCurrentEventData );
		}
	    }
	    
	    if ( handled ) {
		event.stopImmediatePropagation();
   	    }
	    if (activePointers.size < 1 ) {
		gCurrentEventData = null;
	    }
	}
	event.target.releasePointerCapture( event.pointerId );
    }

    function handlePointerCancelEvent( event ) {
	activePointers.clear();
	gCurrentEventData.update( event );

	let handled = Hi.edit.icon.handlePointerUp( gCurrentEventData );
        if ( ! handled) {
	    handled = Hi.location.handlePointerUp( gCurrentEventData );
	}
	if ( handled ) {
	    event.stopImmediatePropagation();
   	}
	gCurrentEventData = null;

	event.target.releasePointerCapture( event.pointerId );
    }
    
    
    $(document).ready(function() {

	addPointerListener( 'pointerdown', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerDownEvent, false );
	addPointerListener( 'pointermove', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerMoveEvent, false );
	addPointerListener( 'pointerup', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerUpEvent );
	addPointerListener( 'pointercancel', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerCancelEvent );
	
	$(document).on('wheel', Hi.LOCATION_VIEW_AREA_SELECTOR, function( event ) {
	    let handled = Hi.edit.icon.handleMouseWheel( event );
	    if ( ! handled ) {
		handled = Hi.location.handleMouseWheel( event );
	    }
	});

	$(document).on('click', Hi.LOCATION_VIEW_AREA_SELECTOR, function( event ) {
	    let handled = Hi.edit.icon.handleClick( event );
	    if ( ! handled ) {
		handled = Hi.edit.path.handleClick( event );
	    }
	    if ( ! handled ) {
		handled = Hi.location.handleClick( event );
	    }
	});

	$(document).on('keydown', function( event ) {
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
		handled = Hi.location.handleKeyDown( event );
	    }
	});
    });
 
})();
