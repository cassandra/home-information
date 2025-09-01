(function() {

    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-location';    
    let gCurrentSelectionModule = null;

    const HiSvgLocation = {
        init: function() {
            Hi.edit.eventBus.subscribe( Hi.edit.SELECTION_MADE_EVENT_NAME,
                                        this.clearSelection.bind(this) );
        },
        handleSinglePointerEventStart: function( singlePointerEvent ) {
            return _handleSinglePointerEventStart( singlePointerEvent );            
        },
        handleSinglePointerEventMove: function( singlePointerEvent ) {
            return _handleSinglePointerEventMove( singlePointerEvent );     
        },
        handleSinglePointerEventEnd: function( singlePointerEvent ) {
            return _handleSinglePointerEventEnd( singlePointerEvent );      
        },
        handleDoublePointerEventStart: function( doublePointerEvent ) {
            return _handleDoublePointerEventStart( doublePointerEvent );            
        },
        handleDoublePointerEventMove: function( doublePointerEvent ) {
            return _handleDoublePointerEventMove( doublePointerEvent );     
        },
        handleDoublePointerEventEnd: function( doublePointerEvent ) {
            return _handleDoublePointerEventEnd( doublePointerEvent );      
        },
        handleLastPointerLocation: function( x, y ) {
            _handleLastPointerLocation( x, y );
        },
        handleMouseWheel: function( event ) {
            return _handleMouseWheel( event );      
        },
        handleClick: function( event ) {
            return _handleClick( event );           
        },
        handleKeyDown: function( event ) {
            return _handleKeyDown( event );         
        },
        clearSelection: function( data ) {
            gCurrentSelectionModule = data.moduleName;
            if ( data.moduleName != MODULE_NAME ) {
                clearSelectedLocationViewSvg();
            }
        }       
    };

    window.Hi.location = HiSvgLocation;
    HiSvgLocation.init();
    
    /* 
      SVG LOCATION
      
      - For panning, zooming and rotating of the underlying background SVG of a location view.
    */

    const SVG_TRANSFORM_ACTION_SCALE_KEY = 's';
    const SVG_TRANSFORM_ACTION_ROTATE_KEY = 'r';
    const SVG_TRANSFORM_ACTION_INCREASE_KEY = '+';
    const SVG_TRANSFORM_ACTION_DECREASE_KEY = '-';

    const KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const KEYPRESS_ROTATE_DEGREES = 10.0;
    const MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_WHEEL_ROTATE_ANGLE = 3.0;
    const SINGLE_POINTER_EVENTS_SCALE_FACTOR = 250.0;
    const DOUBLE_POINTER_EVENTS_SCALE_FACTOR = 250.0;
    const SINGLE_POINTER_EVENTS_ROTATE_FACTOR = 0.5;
    const DOUBLE_POINTER_EVENTS_ROTATE_FACTOR = 0.5;
    const ZOOM_API_CALL_DEBOUNCE_MS = 400;
    
    const LOCATION_VIEW_EDIT_PANE_SELECTOR = '#hi-location-view-edit';
    const API_EDIT_LOCATION_VIEW_GEOMETRY_URL = '/location/edit/view/geometry';

    const SvgTransformType = {
        MOVE: 'move',
        SCALE: 'scale',
        ROTATE: 'rotate'
    };
    let gSvgTransformType = SvgTransformType.MOVE;

    let gSelectedLocationViewSvg = null;
    let gSvgTransformData = null;
    let gLastPointerPosition = { x: 0, y: 0 };
    let gIgnoreCLick = false;  // Set by pointer event handling when no click handling should be done

    let zoomApiCallDebounceTimer = null;
    let lastZoomApiCallTime = 0;
    
    function _handleSinglePointerEventStart( singlePointerEvent ) {
        const event = singlePointerEvent.start.event;

        if ( gSelectedLocationViewSvg ) {
            if ( Hi.DEBUG ) { console.log( `Pointer down event [${MODULE_NAME}]`, event ); }
            createTransformData( event, gSelectedLocationViewSvg );
            return true;
            
        } else if ( gCurrentSelectionModule != 'svg-path' ) {
            const closest = $(event.target).closest( Hi.LOCATION_VIEW_SVG_SELECTOR );
            if ( closest.length > 0 ) {
                if ( Hi.DEBUG ) { console.log( `Pointer down event [${MODULE_NAME}]`, event ); }
                gSelectedLocationViewSvg = closest[0];
                createTransformData( event, gSelectedLocationViewSvg );
                return true;
            }
        }
        
        if ( Hi.DEBUG ) { console.log( `Pointer down skipped: [${MODULE_NAME}]` ); }
        return false;
    }
    
    function _handleSinglePointerEventMove( singlePointerEvent ) {
        const event = singlePointerEvent.last.event;
        
        const currentPointPosition = {
            x: event.clientX,
            y: event.clientY
        };
        if ( gSvgTransformData ) {
            
            gSvgTransformData.isDragging = true;
            if ( gSvgTransformType == SvgTransformType.SCALE ) {
                updateScaleFromPointerMove( event );
            } else if( gSvgTransformType == SvgTransformType.ROTATE ) {
                updateRotationFromPointerMove( singlePointerEvent );
            } else {
                updateDragFromPointerMove( singlePointerEvent );
            }
            gSvgTransformData.last = currentPointPosition;
            return true;
        }
        return false;
    }
    
    function _handleSinglePointerEventEnd( singlePointerEvent ) {

        const event = singlePointerEvent.last.event;

        let eventWasHandled = false;
        if ( gSvgTransformData ) {
            if ( gSvgTransformType == SvgTransformType.SCALE ) {
                endScale();
                eventWasHandled = true;

            } else if( gSvgTransformType == SvgTransformType.ROTATE ) {
                endRotation();
                eventWasHandled = true;

            } else if (( gSvgTransformType == SvgTransformType.MOVE ) && gSvgTransformData.isDragging ) {
                endDrag( event );
                eventWasHandled = true;
            }
        }
        
        if ( eventWasHandled ) {
            if ( Hi.DEBUG ) { console.log( `Pointer end: [${MODULE_NAME}]`, event ); }
            clearTransformData();
            gIgnoreCLick = true;

        } else {
            if ( Hi.DEBUG ) { console.log( `Pointer env skipped: [${MODULE_NAME}]` ); }
        }
        return eventWasHandled;
    }

    function _handleDoublePointerEventStart( doublePointerEvent ) {
        const event = doublePointerEvent.start.event;
        const closest = $(event.target).closest( Hi.LOCATION_VIEW_SVG_SELECTOR );
        if ( closest.length > 0 ) {
            gSelectedLocationViewSvg = closest[0];
            createTransformData( event, gSelectedLocationViewSvg );
            return true;
        }
        return false;
    }

    function _handleDoublePointerEventMove( doublePointerEvent ) {
        if ( ! gSvgTransformData ) {
            return false;
        }
        let scaleFactor = ( 1.0 - ( doublePointerEvent.deltaDistancePrevious
                                    / DOUBLE_POINTER_EVENTS_SCALE_FACTOR ));
        let deltaAngle = doublePointerEvent.deltaAnglePrevious * DOUBLE_POINTER_EVENTS_ROTATE_FACTOR;
        zoom( scaleFactor );
        rotate( deltaAngle );
        return true;
    }

    function _handleDoublePointerEventEnd( doublePointerEvent ) {
        if ( ! gSvgTransformData ) {
            return false;
        }
        saveSvgGeometryDebouncer();
        abortScale();
        abortRotation();
        return true;
    }

    function _handleLastPointerLocation( x, y ) {
        gLastPointerPosition.x = x;
        gLastPointerPosition.y = y;
    }
    
    function _handleMouseWheel( event ) {
        if ( gSelectedLocationViewSvg && isEventInLocationArea( event )) {
            if ( gSvgTransformType == SvgTransformType.ROTATE ) {
                rotateFromMouseWheel( event );

            } else {
                abortScale();
                abortRotation();
                zoomFromMouseWheel( event );
            }
            event.preventDefault(); 
            event.stopImmediatePropagation();
            return true;
        }
        return false;
    }
    
    function _handleClick( event ) {
        if ( gIgnoreCLick ) {
            if ( Hi.DEBUG ) { console.log( `Ignoring click [${MODULE_NAME}]`, event ); }
            gIgnoreCLick = false;
            return true;
        }

        if ( $(event.target).closest( Hi.LOCATION_VIEW_BASE_SELECTOR ).length > 0 ) {
            const closest = $(event.target).closest( Hi.LOCATION_VIEW_SVG_SELECTOR );
            if ( closest.length > 0 ) {
                if ( Hi.DEBUG ) { console.log( `Click handled: [${MODULE_NAME}]`, event ); }
                gSelectedLocationViewSvg = closest[0];
                clearTransformData();
                let data = {
                    moduleName: MODULE_NAME,
                };
                Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, data );
                return true;
            }
        }
        if ( Hi.DEBUG ) { console.log( `Click skipped [${MODULE_NAME}]` ); }
        return false;
    }

    function _handleKeyDown( event ) {
        if ( $(event.target).is('input, textarea') ) {
            return false;
        }
        if ($(event.target).closest('.modal').length > 0) {
            return false;
        }
        if ( gSelectedLocationViewSvg ) {

            const targetArea = $(Hi.LOCATION_VIEW_AREA_SELECTOR);
            const targetOffset = targetArea.offset();
            const targetWidth = targetArea.outerWidth();
            const targetHeight = targetArea.outerHeight();

            if (( gLastPointerPosition.x >= targetOffset.left )
                && ( gLastPointerPosition.x <= ( targetOffset.left + targetWidth ))
                && ( gLastPointerPosition.y >= targetOffset.top )
                && ( gLastPointerPosition.y <= ( targetOffset.top + targetHeight ))) {
                
                if ( Hi.DEBUG ) { console.log( `Key Down [${MODULE_NAME}]`, event ); }
                
                if ( event.key == SVG_TRANSFORM_ACTION_SCALE_KEY ) {
                    abortRotation();
                    startScale();
                    
                } else if ( event.key == SVG_TRANSFORM_ACTION_ROTATE_KEY ) {
                    abortScale();
                    startRotation();
                    
                } else if ( event.key == SVG_TRANSFORM_ACTION_INCREASE_KEY ) {

                    if ( gSvgTransformType === SvgTransformType.ROTATE ) {
                        rotateRightFromKeypress( event );
                    } else {
                        zoomInFromKeypress( event );
                    }
                    
                } else if ( event.key == SVG_TRANSFORM_ACTION_DECREASE_KEY ) {
                    if ( gSvgTransformType === SvgTransformType.ROTATE ) {
                        rotateLeftFromKeypress( event );
                    } else {
                        zoomOutFromKeypress( event );
                    }
                    
                } else if ( event.key == 'Escape' ) {
                    abortScale();
                    abortRotation();
                }
            }
            event.preventDefault();
            event.stopImmediatePropagation();
            return true;
        }
        if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
        return false;
    }

    function isEventInLocationArea( event ) {

        if ( $(event.target).is('input, textarea') ) {
            return false;
        }
        if ($(event.target).closest('.modal').length > 0) {
            return false;
        }
        return $(event.target).closest(Hi.LOCATION_VIEW_AREA_SELECTOR).length > 0;
    }

    function createTransformData( event, locationViewSvg ) {    
        
        let svgViewBox = Hi.svgUtils.getSvgViewBox( locationViewSvg );
        let transform = $(locationViewSvg).attr('transform') || '';
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

        let startX = event.clientX;
        let startY = event.clientY;
        
        gSvgTransformData = {
            isDragging: false,
            start: {
                x: startX,
                y: startY,
                scale: scale,
                rotate: rotate,
                viewBox: svgViewBox
            },
            last: {
                x: startX,
                y: startY,
            }
        };
    }

    function clearTransformData() {     
        gSvgTransformData = null;
        gSvgTransformType = SvgTransformType.MOVE;
    }
    
    function clearSelectedLocationViewSvg() {
        if ( gSelectedLocationViewSvg ) {
            if ( Hi.DEBUG ) { console.log('Clearing location view svg transform data'); }
            gSelectedLocationViewSvg = null;
            clearTransformData();
        }
    }

    function startDrag( event ) {
    }
    
    function updateDragFromPointerMove( singlePointerEvent ) {
        if ( Hi.DEBUG ) { console.log( `updateDragFromPointerMove [${MODULE_NAME}]` ); }
        if ( ! gSelectedLocationViewSvg || ( gSvgTransformData == null )) {
            return;
        }
        
        let pixelsPerSvgUnit = Hi.svgUtils.getPixelsPerSvgUnit( gSelectedLocationViewSvg );
        let deltaSvgUnits = {
            x: ( singlePointerEvent.last.x - singlePointerEvent.start.x ) / pixelsPerSvgUnit.scaleX,
            y: ( singlePointerEvent.last.y - singlePointerEvent.start.y ) / pixelsPerSvgUnit.scaleX
        };

        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );
        deltaSvgUnits = rotateVector( deltaSvgUnits, -1.0 * rotate.angle );
        
        let newX = gSvgTransformData.start.viewBox.x - deltaSvgUnits.x;
        let newY = gSvgTransformData.start.viewBox.y - deltaSvgUnits.y;

        adjustSvgViewBox( gSvgTransformData.start.viewBox,
                          gSvgTransformData.start.viewBox.width,
                          gSvgTransformData.start.viewBox.height,
                          newX,
                          newY );

        return;
    }

    function endDrag( event ) {
        if ( Hi.DEBUG ) { console.log( `endDrag [${MODULE_NAME}]` ); }
        if ( gSvgTransformData && gSvgTransformData.isDragging ) {
            saveSvgGeometryDebouncer();
        }
        gSvgTransformData.isDragging = false;
    }


    function zoomInFromKeypress( event ) {
        let scaleFactor = 1.0 / ( 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 ));
        zoom( scaleFactor );
        saveSvgGeometryDebouncer();
    }
    
    function zoomOutFromKeypress( event ) {
        let scaleFactor = 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        zoom( scaleFactor );
        saveSvgGeometryDebouncer();
    }

    function zoomFromMouseWheel( event ) {

        const e = event.originalEvent;

        // Immediately update the visual
        let scaleFactor = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        if ( e.deltaY > 0 ) {
            scaleFactor = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
        }
        zoom( scaleFactor );
        saveSvgGeometryDebouncer();
    }

    function zoom( scaleFactor ) {
        let initialSvgViewBox = Hi.svgUtils.getSvgViewBox( gSelectedLocationViewSvg );
        scaleSvgViewBox( initialSvgViewBox, scaleFactor );
    }
    
    function startScale( event ) {
        if ( Hi.DEBUG ) { console.log( `startScale [${MODULE_NAME}]` ); }
        gSvgTransformType = SvgTransformType.SCALE;
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, gSvgTransformType );
    }

    function updateScaleFromPointerMove( event ) {
        if ( Hi.DEBUG ) { console.log( `updateScale [${MODULE_NAME}]` ); }

        if ( gSvgTransformData == null ) {
            return;
        }

        let screenCenter = Hi.getScreenCenterPoint( gSelectedLocationViewSvg );
        const startVector = {
            x: gSvgTransformData.start.x- screenCenter.x,
            y: gSvgTransformData.start.y - screenCenter.y
        };
        const endVector = {
            x: event.clientX - screenCenter.x,
            y: event.clientY - screenCenter.y
        };
        const startVectorLength = Math.sqrt( ( startVector.x * startVector.x )
                                             + ( startVector.y * startVector.y ));
        const endVectorLength = Math.sqrt( ( endVector.x * endVector.x )
                                           + ( endVector.y * endVector.y ));
        const vectorLengthDelta = endVectorLength - startVectorLength;

        let scaleFactor = ( 1.0 - ( vectorLengthDelta / SINGLE_POINTER_EVENTS_SCALE_FACTOR ));

        scaleSvgViewBox( gSvgTransformData.start.viewBox, scaleFactor );
    }

    function endScale() {
        if ( Hi.DEBUG ) { console.log( `endScale [${MODULE_NAME}]` ); }
        gSvgTransformType = SvgTransformType.MOVE;      
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );  
        saveSvgGeometryDebouncer();
    }

    function abortScale() {
        if ( Hi.DEBUG ) { console.log( `abortScale [${MODULE_NAME}]` ); }
        clearTransformData();
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
    }

    function scaleSvgViewBox( initialSvgViewBox, scaleFactor ) {

        let newWidth = scaleFactor * initialSvgViewBox.width;
        let newHeight = scaleFactor * initialSvgViewBox.height;
        adjustSvgViewBox( initialSvgViewBox, newWidth, newHeight );
        return;
    }
    
    function startRotation( event ) {
        if ( Hi.DEBUG ) { console.log( `startRotation [${MODULE_NAME}]` ); }
        gSvgTransformType = SvgTransformType.ROTATE;    
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, gSvgTransformType );
    }
    
    function updateRotationFromPointerMove( singlePointerEvent ) {
        if ( Hi.DEBUG ) { console.log( `updateRotationFromPointerMove [${MODULE_NAME}]` ); }

        let screenCenter = Hi.getScreenCenterPoint( gSelectedLocationViewSvg );

        let deltaAngle = Hi.getRotationAngle( screenCenter.x, screenCenter.y,
                                              singlePointerEvent.previous.x, singlePointerEvent.previous.y,
                                              singlePointerEvent.last.x, singlePointerEvent.last.y );

        deltaAngle *= SINGLE_POINTER_EVENTS_ROTATE_FACTOR;
        rotate( deltaAngle );
    }

    function rotateRightFromKeypress( event ) {
        let deltaAngle = KEYPRESS_ROTATE_DEGREES;
        rotate( deltaAngle );
        saveSvgGeometryDebouncer();
    }
    
    function rotateLeftFromKeypress( event ) {
        let deltaAngle = -1.0 * KEYPRESS_ROTATE_DEGREES;
        rotate( deltaAngle );
        saveSvgGeometryDebouncer();
    }

    function rotateFromMouseWheel( event ) {

        const e = event.originalEvent;

        // Immediately update the visual
        let deltaAngle = MOUSE_WHEEL_ROTATE_ANGLE;
        if ( e.deltaY > 0 ) {
            deltaAngle *= -1.0;
        }
        rotate( deltaAngle );
        saveSvgGeometryDebouncer();
    }
    
    function rotate( deltaAngle ) {
        
        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );
        rotate.angle = rotate.angle + deltaAngle;
        rotate.angle = Hi.normalizeAngle( rotate.angle );
        let newTransform = `rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        $(gSelectedLocationViewSvg).attr( 'transform', newTransform );

        // Some browser-device combinations have rendering bugs with the
        // transform property, but not the CSS versions.
        gSelectedLocationViewSvg.style.transform = `rotate( ${rotate.angle}deg )`;
    }
   
    function endRotation( ) {
        if ( Hi.DEBUG ) { console.log( `endRotation [${MODULE_NAME}]` ); }
        gSvgTransformType = SvgTransformType.MOVE;      
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
        saveSvgGeometryDebouncer();     
    }
    
    function abortRotation( ) {
        if ( Hi.DEBUG ) { console.log( `abortRotation [${MODULE_NAME}]` ); }
        clearTransformData();
        $(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
    }
    
    function adjustSvgViewBox( initialSvgViewBox, newWidth, newHeight, newX = null, newY = null ) {

        // Need to account for possible SVG rotation
        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

        // Adjust the dimensions to fill as much as the screen as possible
        let containerRect = $(Hi.LOCATION_VIEW_AREA_SELECTOR)[0].getBoundingClientRect();
        let containerAspectRatio = containerRect.width / containerRect.height;
        let newAspectRatio = newWidth / newHeight;

        if ( newAspectRatio > containerAspectRatio ) {
            newHeight = newWidth / containerAspectRatio;
        } else if ( newAspectRatio < containerAspectRatio ) {
            newWidth = newHeight * containerAspectRatio;
        }

        // Ensure the new viewBox is clamped within the extents of the SVG
        let extentsSvgViewBox = Hi.svgUtils.getExtentsSvgViewBox( gSelectedLocationViewSvg );

        extentsSvgViewBox = calculateRotatedRectangle( extentsSvgViewBox, rotate.angle );
        
        newWidth = Math.min( newWidth, extentsSvgViewBox.width );
        newHeight = Math.min( newHeight, extentsSvgViewBox.height );

        // Center the new viewBox within the initial viewBox (if no explicit newX/newY)
        if ( ! newX ) {
            newX = initialSvgViewBox.x + ( initialSvgViewBox.width - newWidth ) / 2.0;
        }
        if ( ! newY ) {
            newY = initialSvgViewBox.y + ( initialSvgViewBox.height - newHeight ) / 2.0;
        }
        
        if (newX < extentsSvgViewBox.x) {
            newX = extentsSvgViewBox.x;
        }
        if (newY < extentsSvgViewBox.y) {
            newY = extentsSvgViewBox.y;
        }
        if (( newX + newWidth ) > ( extentsSvgViewBox.x + extentsSvgViewBox.width )) {
            newX = extentsSvgViewBox.x + extentsSvgViewBox.width - newWidth;
        }
        if (( newY + newHeight ) > ( extentsSvgViewBox.y + extentsSvgViewBox.height )) {
            newY = extentsSvgViewBox.y + extentsSvgViewBox.height - newHeight;
        }

        Hi.svgUtils.setSvgViewBox( gSelectedLocationViewSvg, newX, newY, newWidth, newHeight );
    }

    function calculateRotatedRectangle( initialRect, rotationAngle ) {

        let corners = [
            { x: initialRect.x, y: initialRect.y },
            { x: initialRect.x + initialRect.width, y: initialRect.y },
            { x: initialRect.x, y: initialRect.y + initialRect.height },
            { x: initialRect.x + initialRect.width, y: initialRect.y + initialRect.height }
        ];
        
        // Rotate the corners around the center of the viewBox
        let centerX = initialRect.x + ( initialRect.width / 2.0 );
        let centerY = initialRect.y + ( initialRect.height / 2.0 );
        let radians = (Math.PI / 180) * rotationAngle;
        
        let rotatedCorners = corners.map((corner) => {
            let dx = corner.x - centerX;
            let dy = corner.y - centerY;
            return {
                x: centerX + (dx * Math.cos(radians) - dy * Math.sin(radians)),
                y: centerY + (dx * Math.sin(radians) + dy * Math.cos(radians)),
            };
        });
        
        // Calculate the new bounding box from the rotated corners
        let minX = Math.min(...rotatedCorners.map(c => c.x));
        let minY = Math.min(...rotatedCorners.map(c => c.y));
        let maxX = Math.max(...rotatedCorners.map(c => c.x));
        let maxY = Math.max(...rotatedCorners.map(c => c.y));
        
        return {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY,
        };
    }

    function rotateVector( point, rotationAngle ) {
        let radians = (Math.PI / 180) * rotationAngle;
        let newX = point.x * Math.cos(radians) - point.y * Math.sin(radians);
        let newY = point.x * Math.sin(radians) + point.y * Math.cos(radians);
        return { x: newX, y: newY };
    }

    function saveSvgGeometryDebouncer() {
        if ( ! shouldSaveGeometry() ) {
            return;
        }
        const currentTime = Date.now();
        const timeSinceLastApiCall = currentTime - lastZoomApiCallTime;

        clearTimeout( zoomApiCallDebounceTimer );
        zoomApiCallDebounceTimer = setTimeout(() => {
            saveSvgGeometryIfNeeded();
            lastZoomApiCallTime = Date.now();
        }, ZOOM_API_CALL_DEBOUNCE_MS );
    }
    
    function saveSvgGeometryIfNeeded( ) {
        if ( ! shouldSaveGeometry() ) {
            return;
        }
        if ( Hi.DEBUG ) { console.log( `Saving SVG geometry [${MODULE_NAME}]` ); }

        let locationViewId = $(gSelectedLocationViewSvg).attr('location-view-id');
        let svgViewBoxStr = $(gSelectedLocationViewSvg).attr('viewBox');
        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

        let data = {
            svg_view_box_str: svgViewBoxStr,
            svg_rotate: rotate.angle
        };
        
        AN.post( `${API_EDIT_LOCATION_VIEW_GEOMETRY_URL}/${locationViewId}`, data );
    }

    function shouldSaveGeometry() {
        /* We only save the current location view geometry on a change if
           the Location View editing pane is showing. automatically saving
           the geometry after all move/scale/rotate operations is more
           inconvenient than helpful.  While editing, it is often useful to
           manipulate the location view geometry while editing and
           arranging the entities.  If these entity refinements happen
           after the the desired geometry has been set, then the act of
           editing those entities and manipulating the location view will
           result in undoing the original geometry work. Further, the user
           only finds this out after they exit editing mode and see that it
           has changed.  Thus, we changed to require an explicit the location
           editing view pane to be visible.
        */
        return ( Hi.isEditMode
                 && gSelectedLocationViewSvg
                 && ( $(LOCATION_VIEW_EDIT_PANE_SELECTOR).length > 0 ));
    }
    
})();
