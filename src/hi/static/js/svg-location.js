(function() {

    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};

    const MODULE_NAME = 'svg-location';    

    const HiSvgLocation = {
        init: function() {
            Hi.edit.eventBus.subscribe( Hi.edit.SELECTION_MADE_EVENT_NAME,
					this.clearSelection.bind(this) );
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
    const SVG_TRANSFORM_ACTION_ZOOM_IN_KEY = '+';
    const SVG_TRANSFORM_ACTION_ZOOM_OUT_KEY = '-';

    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3; // Differentiate between move events and sloppy clicks
    const PIXEL_MOVE_DISTANCE_SCALE_FACTOR = 500.0;
    const ZOOM_SCALE_FACTOR_PERCENT = 10.0;

    const API_EDIT_LOCATION_VIEW_GEOMETRY_URL = '/location/edit/location-view/geometry';
    
    const SvgTransformType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };
    let gSvgTransformType = SvgTransformType.MOVE;

    let gCurrentSelectionModule = null;
    let gSelectedLocationViewSvg = null;
    let gSvgTransformData = null;
    let gLastMousePosition = { x: 0, y: 0 };
    let gIgnoreCLick = false;  // Set by mouseup handling when no click handling should be done

    $(document).ready(function() {

	$(document).on('mousedown', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    handleMouseDown( event );
	});
	$(document).on('mousemove', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    handleMouseMove( event );
	});
	$(document).on('mouseup', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    handleMouseUp( event );
	});
	$(document).on('click', function(event) {
	    handleClick( event );
	});
	$(document).on('keydown', function(event) {
	    handleKeyDown( event );
	});
    });

    function handleMouseDown( event ) {
	if ( gSelectedLocationViewSvg ) {
	    if ( Hi.DEBUG ) { console.log( `Mouse down event [${MODULE_NAME}]`, event ); }
	    createTransformData( event, gSelectedLocationViewSvg );
	    event.preventDefault();
	    event.stopImmediatePropagation();
	    return;
	} else if ( $(event.target).hasClass( Hi.LOCATION_VIEW_SVG_CLASS ) ) {
	    if ( gCurrentSelectionModule != 'svg-path' ) {
		if ( Hi.DEBUG ) { console.log( `Mouse down event [${MODULE_NAME}]`, event ); }
		createTransformData( event, event.target );
		gSelectedLocationViewSvg = event.target;
		event.preventDefault(); 
		event.stopImmediatePropagation();
		return;
	    }
	}
	
	if ( Hi.DEBUG ) { console.log( `Mouse down skipped [${MODULE_NAME}]` ); }
    }
    
    function handleMouseUp( event ) {
	
	if ( gSvgTransformData ) {
	    if ( Hi.DEBUG ) { console.log( `Mouse up event [${MODULE_NAME}]`, event ); }
	    if ( gSvgTransformType == SvgTransformType.SCALE ) {
		applyScale( event );
	    } else if( gSvgTransformType == SvgTransformType.ROTATE ) {
		applyRotation( event );
	    } else {
		if ( gSvgTransformData.isDragging ) {
		    applyDrag( event );
		} else {
		    if ( Hi.DEBUG ) { console.log( `Mouse up skipped [${MODULE_NAME}]` ); }
		    return;
		}
	    }
	    gSvgTransformData = null;
	    gSvgTransformType = SvgTransformType.MOVE;
	    gIgnoreCLick = true;

	    event.preventDefault(); 
	    event.stopImmediatePropagation();
	    return;
	}
	
	if ( Hi.DEBUG ) { console.log( `Mouse up skipped [${MODULE_NAME}]` ); }
    }
    
    function handleMouseMove( event ) {
	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	if ( gSvgTransformData ) {
	    
	    const distanceX = Math.abs( currentMousePosition.x - gSvgTransformData.clickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gSvgTransformData.clickStart.y );
	    
	    if ( gSvgTransformData.isDragging
		 || ( distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS )
		 || ( distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS )) {
		gSvgTransformData.isDragging = true;
		if ( gSvgTransformType == SvgTransformType.SCALE ) {
		    updateScale( event );
		} else if( gSvgTransformType == SvgTransformType.ROTATE ) {
		    updateRotation( event );
		} else {
		    updateDrag(event);
		}
		gSvgTransformData.lastMousePosition = currentMousePosition;
		event.preventDefault(); 
	    	event.stopImmediatePropagation();
	    }
	}
	gLastMousePosition = currentMousePosition;
    }
    
    function handleClick( event ) {
	if ( gIgnoreCLick ) {
	    if ( Hi.DEBUG ) { console.log( `Ignoring click [${MODULE_NAME}]`, event ); }
	    gIgnoreCLick = false;
	    event.preventDefault();
	    event.stopImmediatePropagation();
	    return;
	}

	if ( $(event.target).hasClass( Hi.LOCATION_VIEW_SVG_CLASS ) ) {
	    if ( Hi.DEBUG ) { console.log( `Click [${MODULE_NAME}]`, event ); }
	    gSelectedLocationViewSvg = event.target;
	    gSvgTransformData = null;
	    gSvgTransformType = SvgTransformType.MOVE;
	    event.preventDefault(); 
	    event.stopImmediatePropagation();
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Click skipped [${MODULE_NAME}]` ); }
    }

    function handleKeyDown( event ) {
	if ( $(event.target).is('input, textarea') ) {
            return;
	}
	if ( gSelectedLocationViewSvg ) {

	    const targetArea = $(Hi.LOCATION_VIEW_AREA_SELECTOR);
            const targetOffset = targetArea.offset();
            const targetWidth = targetArea.outerWidth();
            const targetHeight = targetArea.outerHeight();

            if (( gLastMousePosition.x >= targetOffset.left )
		&& ( gLastMousePosition.x <= ( targetOffset.left + targetWidth ))
		&& ( gLastMousePosition.y >= targetOffset.top )
		&& ( gLastMousePosition.y <= ( targetOffset.top + targetHeight ))) {
		
		if ( Hi.DEBUG ) { console.log( `Key Down [${MODULE_NAME}]`, event ); }
		
		if ( event.key == SVG_TRANSFORM_ACTION_SCALE_KEY ) {
		    abortRotation();
		    startScale();
		    
		} else if ( event.key == SVG_TRANSFORM_ACTION_ROTATE_KEY ) {
		    abortScale();
		    startRotation();
		    
		} else if ( event.key == SVG_TRANSFORM_ACTION_ZOOM_IN_KEY ) {
		    abortScale();
		    abortRotation();
		    zoomIn( event );
		    
		} else if ( event.key == SVG_TRANSFORM_ACTION_ZOOM_OUT_KEY ) {
		    abortScale();
		    abortRotation();
		    zoomOut( event );
		    
		} else if ( event.key == 'Escape' ) {
		    abortScale();
		    abortRotation();
		}
 		event.preventDefault();
		event.stopImmediatePropagation();
		return;
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
    }

    function createTransformData( event, locationViewSvg ) {	
	
	let svgViewBox = Hi.getSvgViewBox( locationViewSvg );
        let transform = $(locationViewSvg).attr('transform') || '';
        let { scale, translate, rotate } = Hi.getSvgTransformValues( transform );

	gSvgTransformData = {
	    isDragging: false,
	    clickStart: {
		x: event.clientX,
		y: event.clientY,
		time: Date.now()
	    },
	    lastMousePosition: {
		x: event.clientX,
		y: event.clientY,
	    },
	    initialSvgRotate: rotate,
	    initialSvgViewBox: svgViewBox
	};
    }

    function clearSelectedLocationViewSvg() {
	if ( gSelectedLocationViewSvg ) {
            if ( Hi.DEBUG ) { console.log('Clearing location view svg transform data'); }
	    gSelectedLocationViewSvg = null;
	    gSvgTransformData = null;
	}
    }

    function startDrag( event ) {
    }
    
    function updateDrag( event ) {
	if ( Hi.DEBUG ) { console.log( `updateDrag [${MODULE_NAME}]` ); }
	if ( gSvgTransformData == null ) {
	    return;
	}

	let pixelsPerSvgUnit = Hi.getPixelsPerSvgUnit( gSelectedLocationViewSvg );
        let deltaSvgUnits = {
	    x: ( event.clientX - gSvgTransformData.clickStart.x ) / pixelsPerSvgUnit.scaleX,
	    y: ( event.clientY - gSvgTransformData.clickStart.y ) / pixelsPerSvgUnit.scaleX
	};

	let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.getSvgTransformValues( transform );
	deltaSvgUnits = rotateVector( deltaSvgUnits, -1.0 * rotate.angle );
	
	let newX = gSvgTransformData.initialSvgViewBox.x - deltaSvgUnits.x;
	let newY = gSvgTransformData.initialSvgViewBox.y - deltaSvgUnits.y;

	adjustSvgViewBox( gSvgTransformData.initialSvgViewBox,
			  gSvgTransformData.initialSvgViewBox.width,
			  gSvgTransformData.initialSvgViewBox.height,
			  newX,
			  newY );

	return;
    }

    function applyDrag( event ) {
	if ( Hi.DEBUG ) { console.log( `applyDrag [${MODULE_NAME}]` ); }
	if ( gSvgTransformData && gSvgTransformData.isDragging ) {
	    gSvgTransformData.isDragging = false;
	    saveSvgGeometryIfNeeded();
	}
    }


    function zoomIn( event ) {
	let scaleFactor = 1.0 / ( 1.0 + ( ZOOM_SCALE_FACTOR_PERCENT / 100.0 ));
	let initialSvgViewBox = Hi.getSvgViewBox( gSelectedLocationViewSvg );
	scaleSvgViewBox( initialSvgViewBox, scaleFactor );
	saveSvgGeometryIfNeeded();
    }
    
    function zoomOut( event ) {
	let scaleFactor = 1.0 + ( ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	let initialSvgViewBox = Hi.getSvgViewBox( gSelectedLocationViewSvg );
	scaleSvgViewBox( initialSvgViewBox, scaleFactor );
	saveSvgGeometryIfNeeded();
    }
    
    function startScale( event ) {
	if ( Hi.DEBUG ) { console.log( `startScale [${MODULE_NAME}]` ); }

	gSvgTransformType = SvgTransformType.SCALE;
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, gSvgTransformType );
    }

    function updateScale( event ) {
	if ( Hi.DEBUG ) { console.log( `updateScale [${MODULE_NAME}]` ); }

	if ( gSvgTransformData == null ) {
	    return;
	}

	let screenCenter = Hi.getScreenCenterPoint( gSelectedLocationViewSvg );
	const startVector = {
	    x: gSvgTransformData.clickStart.x- screenCenter.x,
	    y: gSvgTransformData.clickStart.y - screenCenter.y
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

	let scaleFactor = ( 1.0 - ( vectorLengthDelta / PIXEL_MOVE_DISTANCE_SCALE_FACTOR ));

	scaleSvgViewBox( gSvgTransformData.initialSvgViewBox, scaleFactor );
    }

    function applyScale( event ) {
	if ( Hi.DEBUG ) { console.log( `applyScale [${MODULE_NAME}]` ); }
	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );	
	saveSvgGeometryIfNeeded();
    }

    function abortScale( event ) {
	if ( Hi.DEBUG ) { console.log( `abortScale [${MODULE_NAME}]` ); }
	gSvgTransformData = null;
	gSvgTransformType = SvgTransformType.MOVE;	
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
    
    function updateRotation( event ) {
	if ( Hi.DEBUG ) { console.log( `updateRotation [${MODULE_NAME}]` ); }

	let screenCenter = Hi.getScreenCenterPoint( gSelectedLocationViewSvg );

	let deltaAngle = Hi.getRotationAngle( screenCenter.x, screenCenter.y,
					      gLastMousePosition.x, gLastMousePosition.y,
					      event.clientX, event.clientY );

        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = Hi.normalizeAngle( rotate.angle );

	let newTransform = `rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        $(gSelectedLocationViewSvg).attr( 'transform', newTransform );

    }
    
    function applyRotation( event ) {
	if ( Hi.DEBUG ) { console.log( `applyRotation [${MODULE_NAME}]` ); }
	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
	saveSvgGeometryIfNeeded();	
    }
    
    function abortRotation( event ) {
	if ( Hi.DEBUG ) { console.log( `abortRotation [${MODULE_NAME}]` ); }
	gSvgTransformData = null;
	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
    }

    function adjustSvgViewBox( initialSvgViewBox, newWidth, newHeight, newX = null, newY = null ) {

	// Need to account for possible SVG rotation
        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.getSvgTransformValues( transform );

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
	let extentsSvgViewBox = Hi.getExtentsSvgViewBox( gSelectedLocationViewSvg );

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

	let svgViewBoxStr = `${newX} ${newY} ${newWidth} ${newHeight}`;
        $(gSelectedLocationViewSvg).attr('viewBox', svgViewBoxStr );	    	
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

    function saveSvgGeometryIfNeeded( ) {
	if ( ! Hi.isEditMode || ! gSelectedLocationViewSvg ) {
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Saving SVG geometry [${MODULE_NAME}]` ); }

	let locationViewId = $(gSelectedLocationViewSvg).attr('location-view-id');
	let svgViewBoxStr = $(gSelectedLocationViewSvg).attr('viewBox');
        let transform = $(gSelectedLocationViewSvg).attr('transform');
        let { scale, translate, rotate } = Hi.getSvgTransformValues( transform );

	let data = {
	    svg_view_box_str: svgViewBoxStr,
	    svg_rotate: rotate.angle
	};
	
	AN.post( `${API_EDIT_LOCATION_VIEW_GEOMETRY_URL}/${locationViewId}`, data );
    }
    
})();
