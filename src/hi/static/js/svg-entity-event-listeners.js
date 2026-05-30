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
    const POTENTIAL_CLICK_TIME_DELTA_THRESHOLD_MS = 150;
    const POTENTIAL_CLICK_POSITION_DELTA_THRESHOLD = 5;
    const POTENTIAL_CLICK_DELAY_MS = 50;

    // Synthetic long-press gesture. The listener layer manages
    // timing and movement cancellation, then dispatches to the same
    // icon -> path -> location chain as the other pointer events. It
    // has no opinion about what should happen on a long-press -- each
    // consuming module decides for itself.
    const LONG_PRESS_DURATION_MS = 750;
    const LONG_PRESS_MOVE_THRESHOLD_PIXELS = 5;

    const activePointers = new Map();
    const gLastMoveEventTimes = new Map();
    let gCurrentSingleEvent = null;
    let gCurrentDoubleEvent = null;
    // Tracks pointer down/up events to generate synthetic click events when real clicks don't fire (e.g., MacBook trackpads on SVG elements)
    let gPotentialClickState = null;
    let gLongPressState = null;
    let gSuppressNextClick = false;
	
    class SinglePointerEvent {
	constructor( startEvent ) {
            this.start = {
		event: startEvent,
		x: startEvent.clientX,
		y: startEvent.clientY,
            };
	    
            this.previous = { ...this.start };
            this.last = { ...this.start };
	}
	get deltaXStart() {
            return this.last.x - this.start.x;
	}
	get deltaXPrevious() {
            return this.last.x - this.previous.x;
	}
	get deltaYStart() {
            return this.last.y - this.start.y;
	}
	get deltaYPrevious() {
            return this.last.y - this.previous.y;
	}
	update( newEvent ) {
	    this.previous = { ...this.last };
	    this.last.event = newEvent;
	    this.last.x = newEvent.clientX;
	    this.last.y = newEvent.clientY;
	}
    }

    class DoublePointerEvent {
	constructor( startEvent, pointersMap ) {
	    const points = this.sortedPointsFromPointersMap( pointersMap );
            this.start = {
		event: startEvent,
		points: points,
		distance: this.getDistance( points[1], points[0] ),
		angle: this.getAngle( points[1], points[0] )
            };
	    
            this.previous = { ...this.start };
            this.last = { ...this.start };
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
	sortedPointsFromPointersMap( pointersMap ) {
	    return Array.from( pointersMap.entries() )
		.sort( ([idA], [idB]) => idA - idB)
		.map( ([, value]) => value);
	}
	getDistance( p1, p2 ) {
	    let dx = p1.x - p2.x;
	    let dy = p1.y - p2.y;
	    return Math.sqrt( dx * dx + dy * dy );
	}
	getAngle( p1, p2 ) {
	    return Math.atan2( p2.y - p1.y, p2.x - p1.x ) * ( 180 / Math.PI );
	}
	update( newEvent, pointersMap ) {
	    const points = this.sortedPointsFromPointersMap( pointersMap );
	    this.previous = { ...this.last };
	    this.last.event = newEvent;
	    this.last.points = points;
	    this.last.distance = this.getDistance( points[1], points[0] );
	    this.last.angle = this.getAngle( points[1], points[0] );
	}
    }

    function shouldIgnoreEvent( event ) {
	if (event.pointerType === "touch" || event.pointerType === "pen") {
	    return false;
	}
	else if (event.pointerType === "mouse") {
            return event.buttons != 1;  // Left button only
	}
	return false;
    }

    function startPotentialClickTracking(event) {
	gPotentialClickState = {
	    startTimeMs: performance.now(),
	    startPosition: { x: event.clientX, y: event.clientY },
	    pointerId: event.pointerId
	};
    }

    function checkAndHandlePotentialClick(event, initialActivePointersSize, currentActivePointersSize) {
	if (!gPotentialClickState || 
	    event.pointerId !== gPotentialClickState.pointerId ||
	    initialActivePointersSize !== 1 || 
	    currentActivePointersSize !== 0) {
	    return;
	}
	
	const timeDeltaMs = performance.now() - gPotentialClickState.startTimeMs;
	const positionDeltaX = Math.abs(event.clientX - gPotentialClickState.startPosition.x);
	const positionDeltaY = Math.abs(event.clientY - gPotentialClickState.startPosition.y);
	const positionDeltaMax = Math.max(positionDeltaX, positionDeltaY);

	if (timeDeltaMs < POTENTIAL_CLICK_TIME_DELTA_THRESHOLD_MS && 
	    positionDeltaMax < POTENTIAL_CLICK_POSITION_DELTA_THRESHOLD) {
	    
	    gPotentialClickState.waitingForClick = true;
	    
	    setTimeout(() => {
		if (gPotentialClickState?.waitingForClick) {
		    const clickEvent = new MouseEvent('click', {
			bubbles: true,
			cancelable: true,
			clientX: event.clientX,
			clientY: event.clientY,
			button: event.button
		    });
		    event.target.dispatchEvent(clickEvent);
		    gPotentialClickState = null;
		}
	    }, POTENTIAL_CLICK_DELAY_MS);
	} else {
	    gPotentialClickState = null;
	}
    }
    
    function startLongPressTracking( event ) {
	// Defensive: clear any prior state whose pointerup never
	// arrived (e.g., a missed event from ``setPointerCapture``
	// edge cases) so its ``setTimeout`` handle isn't leaked.
	cancelLongPress();
	gLongPressState = {
	    pointerId: event.pointerId,
	    startEvent: event,
	    startPosition: { x: event.clientX, y: event.clientY },
	    triggerTimer: setTimeout( function() {
		fireLongPress();
	    }, LONG_PRESS_DURATION_MS ),
	};
    }

    function cancelLongPress() {
	if ( ! gLongPressState ) { return; }
	clearTimeout( gLongPressState.triggerTimer );
	gLongPressState = null;
    }

    function checkLongPressMove( event ) {
	if ( ! gLongPressState ) { return; }
	if ( event.pointerId !== gLongPressState.pointerId ) { return; }
	const dx = Math.abs( event.clientX - gLongPressState.startPosition.x );
	const dy = Math.abs( event.clientY - gLongPressState.startPosition.y );
	if ( Math.max( dx, dy ) > LONG_PRESS_MOVE_THRESHOLD_PIXELS ) {
	    cancelLongPress();
	}
    }

    function fireLongPress() {
	if ( ! gLongPressState ) { return; }
	const startEvent = gLongPressState.startEvent;
	gLongPressState = null;
	// Side effects (suppress the trailing click, tactile feedback)
	// only apply when a consumer actually claimed the gesture.
	// Without this gate, edit-mode interactions silently lose their
	// trailing click to ``gSuppressNextClick`` even though no
	// consumer ran (edit mode's icon handler returns ``false``).
	const handled = dispatchLongPress( startEvent );
	if ( handled ) {
	    gSuppressNextClick = true;
	    // Stale-flag safety: if the expected trailing click never
	    // arrives (pointer leaves the document, scroll preempt,
	    // etc.) auto-clear so we don't silently eat the next
	    // unrelated click many seconds later.
	    setTimeout( function() { gSuppressNextClick = false; }, 1000 );
	    if ( navigator.vibrate ) {
		navigator.vibrate( 50 );
	    }
	}
    }

    function dispatchLongPress( startEvent ) {
	let handled = Hi.edit.icon.handleLongPress( startEvent );
	if ( ! handled ) {
	    handled = Hi.edit.path.handleLongPress( startEvent );
	}
	if ( ! handled ) {
	    handled = Hi.location.handleLongPress( startEvent );
	}
	return handled;
    }

    function handlePointerDownEvent( event ) {
	if ( shouldIgnoreEvent( event )) { return; }

	const initialActivePointersSize = activePointers.size;
	activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );
	const currentActivePointersSize = activePointers.size;

	// Start potential click tracking for single pointer events
	if (currentActivePointersSize === 1) {
	    startPotentialClickTracking(event);
	    startLongPressTracking(event);
	} else {
	    // Multi-touch is for pan/zoom/rotate; long-press is single-finger only.
	    cancelLongPress();
	}

	if (( initialActivePointersSize === 0 ) && ( currentActivePointersSize === 1 )) {
	    gCurrentSingleEvent = new SinglePointerEvent( event );
	    dispatchSinglePointerEventStart( event, gCurrentSingleEvent );
	    
	} else if (( initialActivePointersSize === 1 ) && ( currentActivePointersSize === 2 )) {
	    dispatchSinglePointerEventEnd( null, gCurrentSingleEvent );
	    gCurrentSingleEvent = null;

	    gCurrentDoubleEvent = new DoublePointerEvent( event, activePointers );
	    dispatchDoublePointerEventStart( event, gCurrentDoubleEvent );
	    
	} else if (( initialActivePointersSize == 2 ) && ( currentActivePointersSize === 3 )) {
	    // Only one and two pointer events supported.
	} else {
	    // Only one and two pointer events supported.
	}

	event.target.setPointerCapture( event.pointerId );
	dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerMoveEvent( event ) {
	if ( shouldIgnoreEvent( event )) { return; }
	
	let lastPointer = activePointers.get( event.pointerId );
	if ( ! lastPointer ) {
	    return;
	}

	// Long-press cancellation runs before the move-throttle so even
	// throttled events count toward the cumulative-displacement
	// threshold (cheap check, no DOM work).
	checkLongPressMove( event );

	// Guarding against event floods and performance issues.
	let now = Date.now();
	if ( gLastMoveEventTimes.has( event.pointerId )) {
	    const deltaTimeMs = now - gLastMoveEventTimes.get( event.pointerId );
	    if ( deltaTimeMs < LAST_MOVE_THROTTLE_THRESHOLD_MS ) {
		return;
	    }
	}
	gLastMoveEventTimes.set( event.pointerId, now );
	
        let last_pointer_delta_x = event.clientX - lastPointer.x;
        let last_pointer_delta_y = event.clientY - lastPointer.y;

	// Ignore micro-movements to avoid re-render floods and performance issues.
        if (( Math.abs( last_pointer_delta_x ) < POINTER_MOVE_THRESHOLD_PIXELS )
	    && ( Math.abs( last_pointer_delta_y ) < POINTER_MOVE_THRESHOLD_PIXELS )) {
	    return;
        }

	activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );

	if ( activePointers.size === 1 ) {
	    if (gCurrentSingleEvent) {
		gCurrentSingleEvent.update( event );
		dispatchSinglePointerEventMove( event, gCurrentSingleEvent );
	    }
	    
	} else if ( activePointers.size === 2 ) {
	    if (gCurrentDoubleEvent) {
		gCurrentDoubleEvent.update( event, activePointers );
		dispatchDoublePointerEventMove( event, gCurrentDoubleEvent );
	    }

	} else {
	    // Only one and two pointer events supported.
	}
	dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerUpEvent( event ) {

	const initialActivePointersSize = activePointers.size;
	let lastPointer = activePointers.get( event.pointerId );
	if ( ! lastPointer ) {
	    return;
	}
	activePointers.delete( event.pointerId );
	gLastMoveEventTimes.delete( event.pointerId );
	const currentActivePointersSize = activePointers.size;

	// Released before the long-press trigger fired -- treat as a
	// normal click; cancellation is a no-op if the timer already
	// fired and cleared the state.
	if ( gLongPressState && gLongPressState.pointerId === event.pointerId ) {
	    cancelLongPress();
	}

	// Reset potential click state when switching to multi-touch
	if (currentActivePointersSize > 1) {
	    gPotentialClickState = null;
	}

	// Check for potential click (trackpad compatibility)
	checkAndHandlePotentialClick(event, initialActivePointersSize, currentActivePointersSize);

	if (( initialActivePointersSize === 1 ) && ( currentActivePointersSize === 0 )) {
	    if (gCurrentSingleEvent) {
		gCurrentSingleEvent.update( event );
		dispatchSinglePointerEventEnd( event, gCurrentSingleEvent );
	    }

	} else if (( initialActivePointersSize === 2 ) && ( currentActivePointersSize === 1 )) {
	    dispatchDoublePointerEventEnd( null, gCurrentDoubleEvent );
	    gCurrentDoubleEvent = null;

	    gCurrentSingleEvent = new SinglePointerEvent( event );
	    dispatchSinglePointerEventStart( event, gCurrentSingleEvent );
	    
	} else if (( initialActivePointersSize === 3 ) && ( currentActivePointersSize === 2 )) {
	    dispatchDoublePointerEventEnd( null, gCurrentDoubleEvent );

	    gCurrentDoubleEvent = new DoublePointerEvent( event, activePointers );
	    dispatchDoublePointerEventStart( event, gCurrentDoubleEvent );
	    
	} else {
	    // Only one and two pointer events supported.
	}
	
	event.target.releasePointerCapture( event.pointerId );
	dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerCancelEvent( event ) {
	// Browser-initiated cancellation (scroll start, gesture
	// preempt) may target a pointer ID that ``handlePointerUp``'s
	// active-pointer check rejects, leaving a pending long-press
	// timer alive. Kill it unconditionally before falling through.
	cancelLongPress();
	// Treat the same as an "up" event for now.
	handlePointerUpEvent(event);
    }

    function dispatchLastPointerPosition( x, y ) {
	Hi.edit.icon.handleLastPointerLocation( x, y );
	Hi.location.handleLastPointerLocation( x, y );
    }
    
    function dispatchSinglePointerEventStart( currentEvent, singlePointerEvent ) {
	let handled = Hi.edit.icon.handleSinglePointerEventStart( singlePointerEvent );
	if ( handled ) {
	    Hi.SvgPathCore.clearSelection();
	}
	if ( ! handled) {
	    handled = Hi.edit.path.handleSinglePointerEventStart( singlePointerEvent );
	    if ( handled ) {
		Hi.SvgIconCore.clearSelection();
	    }
	}
        if ( ! handled) {
	    handled = Hi.location.handleSinglePointerEventStart( singlePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.stopImmediatePropagation();
   	}
    }

    function dispatchSinglePointerEventMove( currentEvent, singlePointerEvent ) {
	let handled = Hi.edit.icon.handleSinglePointerEventMove( singlePointerEvent );
	if ( ! handled) {
	    handled = Hi.edit.path.handleSinglePointerEventMove( singlePointerEvent );
	}
	if ( ! handled) {
	    handled = Hi.location.handleSinglePointerEventMove( singlePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.stopImmediatePropagation();
   	}
    }

    function dispatchSinglePointerEventEnd( currentEvent, singlePointerEvent ) {
	let handled = Hi.edit.icon.handleSinglePointerEventEnd( singlePointerEvent );
	if ( ! handled) {
	    handled = Hi.edit.path.handleSinglePointerEventEnd( singlePointerEvent );
	}
	if ( ! handled) {
	    handled = Hi.location.handleSinglePointerEventEnd( singlePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.preventDefault();
	    currentEvent.stopImmediatePropagation();
   	}
    }
    
    
    function dispatchDoublePointerEventStart( currentEvent, doublePointerEvent ) {
	let handled = Hi.edit.icon.handleDoublePointerEventStart( doublePointerEvent );
	if ( ! handled) {
	    handled = Hi.location.handleDoublePointerEventStart( doublePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.stopImmediatePropagation();
   	}
    }

    function dispatchDoublePointerEventMove( currentEvent, doublePointerEvent ) {
	let handled = Hi.edit.icon.handleDoublePointerEventMove( doublePointerEvent );
	if ( ! handled) {
	    handled = Hi.location.handleDoublePointerEventMove( doublePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.stopImmediatePropagation();
   	}
    }

    function dispatchDoublePointerEventEnd( currentEvent, doublePointerEvent ) {
	let handled = Hi.edit.icon.handleDoublePointerEventEnd( doublePointerEvent );
	if ( ! handled) {
	    handled = Hi.location.handleDoublePointerEventEnd( doublePointerEvent );
	}
	if ( handled && currentEvent ) {
	    currentEvent.stopImmediatePropagation();
   	}
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
    
    $(document).ready(function() {

	addPointerListener( 'pointerdown', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerDownEvent, false );
	addPointerListener( 'pointermove', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerMoveEvent, false );
	addPointerListener( 'pointerup', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerUpEvent, false );
	addPointerListener( 'pointercancel', Hi.LOCATION_VIEW_AREA_SELECTOR, handlePointerCancelEvent );
	
	$(document).on('wheel', Hi.LOCATION_VIEW_AREA_SELECTOR, function( event ) {
	    let handled = Hi.edit.icon.handleMouseWheel( event );
	    if ( ! handled ) {
		handled = Hi.location.handleMouseWheel( event );
	    }
	    if ( handled ) {
		event.preventDefault();
		event.stopImmediatePropagation();
   	    }
	});

	$(document).on('click', Hi.LOCATION_VIEW_AREA_SELECTOR, function( event ) {
	    if ( shouldIgnoreEvent( event )) { return; }

	    // Long-press already dispatched the status request; the
	    // browser's trailing click on pointer-up must not also fire
	    // the default action (which in AUTOMATION view would be the
	    // one-click control).
	    if ( gSuppressNextClick ) {
		gSuppressNextClick = false;
		event.preventDefault();
		event.stopImmediatePropagation();
		return;
	    }

	    // Cancel synthetic click if real click event fires
	    if (gPotentialClickState?.waitingForClick) {
		gPotentialClickState = null;
	    }
	    
	    /* Pan-zoom click suppression first — a completed pan drag
	       must not be interpreted as a selection by other modules. */
	    let handled = Hi.location.handleClick( event );
	    if ( ! handled ) {
		handled = Hi.edit.icon.handleClick( event );
	    }
	    if ( ! handled ) {
		handled = Hi.edit.path.handleClick( event );
	    }
	    if ( handled ) {
		event.preventDefault();
		event.stopImmediatePropagation();
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
	    if ( handled ) {
		event.preventDefault();
		event.stopImmediatePropagation();
   	    }
	});
    });
 
})();
