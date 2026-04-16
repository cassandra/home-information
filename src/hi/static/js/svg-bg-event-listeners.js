/*
  SVG Background Editor Event Listeners

  Normalizes browser pointer/mouse/wheel/keyboard events and dispatches
  them to the background editor's core modules. Modeled on
  svg-event-listeners.js but routes to pan-zoom-core, icon-core, and
  path-core instead of entity modules.

  Dispatch priority:
    1. Icon core (if an icon is selected or clicked)
    2. Path core (if a path is selected or clicked)
    3. Pan/zoom core (fallback — pan/zoom the whole canvas)
*/

(function() {

    window.Hi = window.Hi || {};

    const CANVAS_AREA_SELECTOR = '#hi-svg-edit-canvas';

    const LAST_MOVE_THROTTLE_THRESHOLD_MS = 10;
    const POINTER_MOVE_THRESHOLD_PIXELS = 2;
    const POTENTIAL_CLICK_TIME_DELTA_THRESHOLD_MS = 150;
    const POTENTIAL_CLICK_POSITION_DELTA_THRESHOLD = 5;
    const POTENTIAL_CLICK_DELAY_MS = 50;

    const activePointers = new Map();
    const gLastMoveEventTimes = new Map();
    let gCurrentSingleEvent = null;
    let gCurrentDoubleEvent = null;
    let gPotentialClickState = null;

    /* ==================== */
    /* Event Classes        */
    /* ==================== */

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
        get deltaXStart() { return this.last.x - this.start.x; }
        get deltaXPrevious() { return this.last.x - this.previous.x; }
        get deltaYStart() { return this.last.y - this.start.y; }
        get deltaYPrevious() { return this.last.y - this.previous.y; }
        update( newEvent ) {
            this.previous = { ...this.last };
            this.last.event = newEvent;
            this.last.x = newEvent.clientX;
            this.last.y = newEvent.clientY;
        }
    }

    class DoublePointerEvent {
        constructor( startEvent, pointersMap ) {
            var points = this.sortedPointsFromPointersMap( pointersMap );
            this.start = {
                event: startEvent,
                points: points,
                distance: this.getDistance( points[1], points[0] ),
                angle: this.getAngle( points[1], points[0] ),
            };
            this.previous = { ...this.start };
            this.last = { ...this.start };
        }
        get deltaDistanceStart() { return this.last.distance - this.start.distance; }
        get deltaDistancePrevious() { return this.last.distance - this.previous.distance; }
        get deltaAngleStart() { return this.last.angle - this.start.angle; }
        get deltaAnglePrevious() { return this.last.angle - this.previous.angle; }
        sortedPointsFromPointersMap( pointersMap ) {
            return Array.from( pointersMap.entries() )
                .sort( function( a, b ) { return a[0] - b[0]; } )
                .map( function( entry ) { return entry[1]; } );
        }
        getDistance( p1, p2 ) {
            var dx = p1.x - p2.x;
            var dy = p1.y - p2.y;
            return Math.sqrt( dx * dx + dy * dy );
        }
        getAngle( p1, p2 ) {
            return Math.atan2( p2.y - p1.y, p2.x - p1.x ) * ( 180 / Math.PI );
        }
        update( newEvent, pointersMap ) {
            var points = this.sortedPointsFromPointersMap( pointersMap );
            this.previous = { ...this.last };
            this.last.event = newEvent;
            this.last.points = points;
            this.last.distance = this.getDistance( points[1], points[0] );
            this.last.angle = this.getAngle( points[1], points[0] );
        }
    }

    /* ==================== */
    /* Event Filtering      */
    /* ==================== */

    function shouldIgnoreEvent( event ) {
        if ( event.pointerType === 'touch' || event.pointerType === 'pen' ) {
            return false;
        } else if ( event.pointerType === 'mouse' ) {
            return event.buttons != 1;
        }
        return false;
    }

    /* ==================== */
    /* Synthetic Click      */
    /* ==================== */

    function startPotentialClickTracking( event ) {
        gPotentialClickState = {
            startTimeMs: performance.now(),
            startPosition: { x: event.clientX, y: event.clientY },
            pointerId: event.pointerId,
        };
    }

    function checkAndHandlePotentialClick( event, initialSize, currentSize ) {
        if ( ! gPotentialClickState
             || event.pointerId !== gPotentialClickState.pointerId
             || initialSize !== 1
             || currentSize !== 0 ) {
            return;
        }

        var timeDeltaMs = performance.now() - gPotentialClickState.startTimeMs;
        var positionDeltaX = Math.abs( event.clientX - gPotentialClickState.startPosition.x );
        var positionDeltaY = Math.abs( event.clientY - gPotentialClickState.startPosition.y );
        var positionDeltaMax = Math.max( positionDeltaX, positionDeltaY );

        if ( timeDeltaMs < POTENTIAL_CLICK_TIME_DELTA_THRESHOLD_MS
             && positionDeltaMax < POTENTIAL_CLICK_POSITION_DELTA_THRESHOLD ) {

            gPotentialClickState.waitingForClick = true;

            setTimeout( function() {
                if ( gPotentialClickState && gPotentialClickState.waitingForClick ) {
                    var clickEvent = new MouseEvent( 'click', {
                        bubbles: true,
                        cancelable: true,
                        clientX: event.clientX,
                        clientY: event.clientY,
                        button: event.button,
                    });
                    event.target.dispatchEvent( clickEvent );
                    gPotentialClickState = null;
                }
            }, POTENTIAL_CLICK_DELAY_MS );
        } else {
            gPotentialClickState = null;
        }
    }

    /* ==================== */
    /* Pointer Handlers     */
    /* ==================== */

    function handlePointerDownEvent( event ) {
        if ( shouldIgnoreEvent( event ) ) { return; }

        var initialSize = activePointers.size;
        activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );
        var currentSize = activePointers.size;

        if ( currentSize === 1 ) {
            startPotentialClickTracking( event );
        }

        if ( initialSize === 0 && currentSize === 1 ) {
            gCurrentSingleEvent = new SinglePointerEvent( event );
            dispatchSinglePointerEventStart( event, gCurrentSingleEvent );

        } else if ( initialSize === 1 && currentSize === 2 ) {
            dispatchSinglePointerEventEnd( null, gCurrentSingleEvent );
            gCurrentSingleEvent = null;
            gCurrentDoubleEvent = new DoublePointerEvent( event, activePointers );
            dispatchDoublePointerEventStart( event, gCurrentDoubleEvent );
        }

        event.target.setPointerCapture( event.pointerId );
        dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerMoveEvent( event ) {
        if ( shouldIgnoreEvent( event ) ) { return; }

        var lastPointer = activePointers.get( event.pointerId );
        if ( ! lastPointer ) { return; }

        var now = Date.now();
        if ( gLastMoveEventTimes.has( event.pointerId ) ) {
            var deltaTimeMs = now - gLastMoveEventTimes.get( event.pointerId );
            if ( deltaTimeMs < LAST_MOVE_THROTTLE_THRESHOLD_MS ) { return; }
        }
        gLastMoveEventTimes.set( event.pointerId, now );

        var deltaX = event.clientX - lastPointer.x;
        var deltaY = event.clientY - lastPointer.y;
        if ( Math.abs( deltaX ) < POINTER_MOVE_THRESHOLD_PIXELS
             && Math.abs( deltaY ) < POINTER_MOVE_THRESHOLD_PIXELS ) {
            return;
        }

        activePointers.set( event.pointerId, { x: event.clientX, y: event.clientY } );

        if ( activePointers.size === 1 ) {
            if ( gCurrentSingleEvent ) {
                gCurrentSingleEvent.update( event );
                dispatchSinglePointerEventMove( event, gCurrentSingleEvent );
            }
        } else if ( activePointers.size === 2 ) {
            if ( gCurrentDoubleEvent ) {
                gCurrentDoubleEvent.update( event, activePointers );
                dispatchDoublePointerEventMove( event, gCurrentDoubleEvent );
            }
        }
        dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerUpEvent( event ) {
        var initialSize = activePointers.size;
        var lastPointer = activePointers.get( event.pointerId );
        if ( ! lastPointer ) { return; }
        activePointers.delete( event.pointerId );
        gLastMoveEventTimes.delete( event.pointerId );
        var currentSize = activePointers.size;

        if ( currentSize > 1 ) {
            gPotentialClickState = null;
        }

        checkAndHandlePotentialClick( event, initialSize, currentSize );

        if ( initialSize === 1 && currentSize === 0 ) {
            if ( gCurrentSingleEvent ) {
                gCurrentSingleEvent.update( event );
                dispatchSinglePointerEventEnd( event, gCurrentSingleEvent );
            }
        } else if ( initialSize === 2 && currentSize === 1 ) {
            dispatchDoublePointerEventEnd( null, gCurrentDoubleEvent );
            gCurrentDoubleEvent = null;
            gCurrentSingleEvent = new SinglePointerEvent( event );
            dispatchSinglePointerEventStart( event, gCurrentSingleEvent );
        }

        event.target.releasePointerCapture( event.pointerId );
        dispatchLastPointerPosition( event.clientX, event.clientY );
    }

    function handlePointerCancelEvent( event ) {
        handlePointerUpEvent( event );
    }

    /* ==================== */
    /* Dispatch             */
    /* ==================== */

    function dispatchLastPointerPosition( x, y ) {
        Hi.SvgIconCore.handleLastPointerLocation( x, y );
        Hi.SvgPanZoomCore.handleLastPointerLocation( x, y );
        /* Future: path-core position tracking */
    }

    function dispatchSinglePointerEventStart( currentEvent, singlePointerEvent ) {
        var handled = Hi.SvgIconCore.handleSinglePointerEventStart( singlePointerEvent );
        if ( ! handled ) {
            handled = Hi.SvgPanZoomCore.handleSinglePointerEventStart( singlePointerEvent.start.event );
        }
        if ( handled && currentEvent ) {
            currentEvent.stopImmediatePropagation();
        }
    }

    function dispatchSinglePointerEventMove( currentEvent, singlePointerEvent ) {
        var handled = Hi.SvgIconCore.handleSinglePointerEventMove( singlePointerEvent );
        /* Future: try path-core */
        if ( ! handled ) {
            handled = Hi.SvgPanZoomCore.handleSinglePointerEventMove(
                singlePointerEvent.start.event, singlePointerEvent.last.event );
        }
        if ( handled && currentEvent ) {
            currentEvent.stopImmediatePropagation();
        }
    }

    function dispatchSinglePointerEventEnd( currentEvent, singlePointerEvent ) {
        var handled = Hi.SvgIconCore.handleSinglePointerEventEnd( singlePointerEvent );
        if ( ! handled ) {
            handled = Hi.SvgPanZoomCore.handleSinglePointerEventEnd();
        }
        if ( handled && currentEvent ) {
            currentEvent.preventDefault();
            currentEvent.stopImmediatePropagation();
        }
    }

    function dispatchDoublePointerEventStart( currentEvent, doublePointerEvent ) {
        var handled = Hi.SvgIconCore.handleDoublePointerEventStart( doublePointerEvent );
        if ( handled && currentEvent ) {
            currentEvent.stopImmediatePropagation();
        }
    }

    function dispatchDoublePointerEventMove( currentEvent, doublePointerEvent ) {
        var handled = Hi.SvgIconCore.handleDoublePointerEventMove( doublePointerEvent );
        if ( handled && currentEvent ) {
            currentEvent.stopImmediatePropagation();
        }
    }

    function dispatchDoublePointerEventEnd( currentEvent, doublePointerEvent ) {
        var handled = Hi.SvgIconCore.handleDoublePointerEventEnd( doublePointerEvent );
        if ( handled && currentEvent ) {
            currentEvent.stopImmediatePropagation();
        }
    }

    /* ==================== */
    /* Registration Helpers */
    /* ==================== */

    function addPointerListener( eventType, selector, handler, passive ) {
        if ( passive === undefined ) { passive = true; }
        $( document ).each( function() {
            this.addEventListener( eventType, function( event ) {
                if ( event.target.closest( selector ) ) {
                    handler( event );
                }
            }, { passive: passive } );
        });
    }

    /* ==================== */
    /* Initialize           */
    /* ==================== */

    $(document).ready(function() {

        addPointerListener( 'pointerdown', CANVAS_AREA_SELECTOR, handlePointerDownEvent, false );
        addPointerListener( 'pointermove', CANVAS_AREA_SELECTOR, handlePointerMoveEvent, false );
        addPointerListener( 'pointerup', CANVAS_AREA_SELECTOR, handlePointerUpEvent, false );
        addPointerListener( 'pointercancel', CANVAS_AREA_SELECTOR, handlePointerCancelEvent );

        $( document ).on( 'wheel', CANVAS_AREA_SELECTOR, function( event ) {
            var handled = Hi.SvgIconCore.handleMouseWheel( event );
            if ( ! handled ) {
                handled = Hi.SvgPanZoomCore.handleMouseWheel( event );
            }
            if ( handled ) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        });

        $( document ).on( 'click', CANVAS_AREA_SELECTOR, function( event ) {
            if ( gPotentialClickState && gPotentialClickState.waitingForClick ) {
                gPotentialClickState = null;
            }
            var handled = Hi.SvgIconCore.handleClick( event );
            if ( ! handled ) {
                handled = Hi.SvgPathCore.handleClick( event );
            }
            if ( ! handled ) {
                handled = Hi.SvgPanZoomCore.handleClick( event );
            }
            if ( handled ) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        });

        $( document ).on( 'keydown', function( event ) {
            if ( $( event.target ).is( 'input, textarea' ) ) { return; }
            if ( $( event.target ).closest( '.modal' ).length > 0 ) { return; }

            /* Editor-level delete commands — before routing to cores. */
            var handled = false;
            var isDeleteKey = ( event.key === 'x' || event.key === 'Delete' || event.key === 'Backspace' );

            if ( isDeleteKey && ! event.ctrlKey && Hi.SvgIconCore.hasSelection() ) {
                Hi.SvgIconCore.deleteSelectedElement();
                Hi.SvgEdit.onElementDeleted();
                handled = true;

            } else if ( event.key === 'x' && event.ctrlKey && Hi.SvgPathCore.hasSelection() ) {
                Hi.SvgPathCore.deleteSelectedElement();
                Hi.SvgEdit.onElementDeleted();
                handled = true;
            }

            /* Core-level commands. */
            if ( ! handled ) {
                handled = Hi.SvgIconCore.handleKeyDown( event );
            }
            if ( ! handled ) {
                handled = Hi.SvgPathCore.handleKeyDown( event );
            }
            if ( ! handled ) {
                handled = Hi.SvgPanZoomCore.handleKeyDown( event );
            }
            if ( handled ) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        });
    });

})();
