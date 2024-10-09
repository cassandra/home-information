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
	    if ( data != MODULE_NAME ) {
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
	if ( Hi.DEBUG ) { console.log( `Mouse down event [${MODULE_NAME}]`, event ); }

	if ( gSelectedLocationViewSvg ) {
	    createTransformData( event, gSelectedLocationViewSvg );
	    event.preventDefault();
	    event.stopImmediatePropagation();
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Mouse down skipped [${MODULE_NAME}]` ); }
    }
    
    function handleMouseUp( event ) {
	if ( Hi.DEBUG ) { console.log( `Mouse up event [${MODULE_NAME}]`, event ); }
	
	if ( gSvgTransformData && gSvgTransformData.isDragging ) {
	    if ( gSvgTransformType == SvgTransformType.SCALE ) {
		applyScale( event );
	    } else if( gSvgTransformType == SvgTransformType.ROTATE ) {
		applyRotation( event );
	    } else {
		endDrag( event );
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
	gIgnoreCLick = false;

	if ( Hi.DEBUG ) { console.log( `Click [${MODULE_NAME}]`, event ); }
	
	if ( $(event.target).hasClass( Hi.LOCATION_VIEW_SVG_CLASS ) ) {
            if ( Hi.DEBUG ) { console.log( 'SVG Target', event.target ); }
	    handleLocationViewSvgClick( event, event.target );
	    event.preventDefault(); 
	    event.stopImmediatePropagation();
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Click skipped [${MODULE_NAME}]` ); }
    }

    function handleKeyDown( event ) {
	if ( $(event.target).is('input[type="text"], textarea') ) {
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
	    originalSvgRotate: rotate,
	    originalSvgViewBox: svgViewBox
	};
    }

    function clearSelectedLocationViewSvg() {
	if ( gSelectedLocationViewSvg ) {
            if ( Hi.DEBUG ) { console.log('Clearing location view svg transform data'); }
	    gSelectedLocationViewSvg = null;
	    gSvgTransformData = null;
	}
    }

    function handleLocationViewSvgClick( event, locationViewSvg ) {
	gSelectedLocationViewSvg = locationViewSvg;

	if ( Hi.isEditMode ) {
	    Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, MODULE_NAME );
            AN.get( `${Hi.API_SHOW_DETAILS_URL}` );
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
	
	let svgViewBox = {
	    x: gSvgTransformData.originalSvgViewBox.x - deltaSvgUnits.x,
	    y: gSvgTransformData.originalSvgViewBox.y - deltaSvgUnits.y,
	    width: gSvgTransformData.originalSvgViewBox.width,
	    height: gSvgTransformData.originalSvgViewBox.height
	};
	
	let svgViewBoxStr = `${svgViewBox.x} ${svgViewBox.y} ${svgViewBox.width} ${svgViewBox.height}`;
        $(gSelectedLocationViewSvg).attr('viewBox', svgViewBoxStr );	    
    }

    function endDrag( event ) {
	if ( Hi.DEBUG ) { console.log( `endDrag [${MODULE_NAME}]` ); }
	if ( gSvgTransformData && gSvgTransformData.isDragging ) {
	    gSvgTransformData.isDragging = false;
	    if ( Hi.isEditMode ) { 
		let data = {
		    view_box: $(gSelectedLocationViewSvg).attr('viewBox'),
		};
		
		// ZZZ TODO: AN.post( `${API_EDIT_LOCATION_VIEW_VIEWBOX_URL}/${locationViewId}`, data );
	    }
	}
    }


    function zoomIn( event ) {
	let scaleFactor = 1.0 / ( 1.0 + ( ZOOM_SCALE_FACTOR_PERCENT / 100.0 ));
	let originalSvgViewBox = Hi.getSvgViewBox( gSelectedLocationViewSvg );
	adjustSvgViewBox( originalSvgViewBox, scaleFactor );
    }
    
    function zoomOut( event ) {
	let scaleFactor = 1.0 + ( ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	let originalSvgViewBox = Hi.getSvgViewBox( gSelectedLocationViewSvg );
	adjustSvgViewBox( originalSvgViewBox, scaleFactor );
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

	let scale = ( 1.0 - ( vectorLengthDelta / PIXEL_MOVE_DISTANCE_SCALE_FACTOR ));

	adjustSvgViewBox( scale, gSvgTransformData.originalSvgViewBox );
    }

    function adjustSvgViewBox( originalSvgViewBox, scaleFactor ) {
	
	let svgViewBox = {
	    x: originalSvgViewBox.x,
	    y: originalSvgViewBox.y,
	    width: scaleFactor * originalSvgViewBox.width,
	    height: scaleFactor * originalSvgViewBox.height
	};

	let svgOffset = {
	    x: ( originalSvgViewBox.width - svgViewBox.width ) / 2.0,
	    y: ( originalSvgViewBox.height - svgViewBox.height ) / 2.0
	};
	svgViewBox.x += svgOffset.x;
	svgViewBox.y += svgOffset.y;
	
	let svgViewBoxStr = `${svgViewBox.x} ${svgViewBox.y} ${svgViewBox.width} ${svgViewBox.height}`;
        $(gSelectedLocationViewSvg).attr('viewBox', svgViewBoxStr );	    
    }
    
    function applyScale( event ) {
	if ( Hi.DEBUG ) { console.log( `applyScale [${MODULE_NAME}]` ); }

	// ZZZ



	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );	
    }

    function abortScale( event ) {
	if ( Hi.DEBUG ) { console.log( `abortScale [${MODULE_NAME}]` ); }
	gSvgTransformData = null;
	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
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


	
	// ZZZ


	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
	
    }
    
    function abortRotation( event ) {
	if ( Hi.DEBUG ) { console.log( `abortRotation [${MODULE_NAME}]` ); }
	gSvgTransformData = null;
	gSvgTransformType = SvgTransformType.MOVE;	
	$(gSelectedLocationViewSvg).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
    }

    
    
})();
