(function() {

    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};
    window.Hi.svgUtils = window.Hi.svgUtils || {};

    const MODULE_NAME = 'svg-icon';    
    let gCurrentSelectionModule = null;

    const HiEditSvgIcon = {
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
		clearSelectedIconSvgGroup();
            }
        }	
    };

    window.Hi.edit.icon = HiEditSvgIcon;
    HiEditSvgIcon.init();

    /* 
      SVG ICON EDITING
      
      - Icons can be selected to show the entity details in the side edit panel.
      - Icons can be dragged to change their location.
      - Selected icons can be rotated and scaled to change their appearance.
    */
    
    const SELECTABLE_CLASS = 'selectable';
    const SELECTABLE_SELECTOR = '.' + SELECTABLE_CLASS;
    
    const ICON_ACTION_SCALE_KEY = 's';
    const ICON_ACTION_ROTATE_KEY = 'r';
    const ICON_ACTION_ZOOM_IN_KEY = '+';
    const ICON_ACTION_ZOOM_OUT_KEY = '-';

    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3; // Differentiate between move events and sloppy clicks
    const POINTER_EVENTS_SCALE_FACTOR = 250.0;
    const POINTER_EVENTS_ROTATE_FACTOR = 0.1;
    const KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT = 10.0;
    const MOUSE_MOVE_ZOOM_SCALE_FACTOR = 175.0; // Number of pixels moved to double or halve size
    const MOUSE_WHEEL_ROTATE_DEGREES = 10.0;
    const KEYPRESS_ROTATE_DEGREES = 10.0;
    const POSITION_API_CALL_DEBOUNCE_MS = 400;
    
    const API_EDIT_LOCATION_ITEM_POSITION_URL = '/location/edit/location-item/position';
        
    const SvgActionStateType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };
    
    let gSvgIconActionState = SvgActionStateType.MOVE;
    let gSelectedIconSvgGroup = null;
    let gSvgIconDragData = null;
    let gSvgIconActionEditData = null;  // For scale and rotate actions

    let gClickStart = null;
    let gLastMousePosition = { x: 0, y: 0 };
    let gIgnoreCLick = false;  // Set by mouseup handling when no click handling should be done

    let positionApiCallDebounceTimer = null;
    let lastPositionApiCallTime = 0;
    
    function _handleSinglePointerEventStart( singlePointerEvent ) {
	if ( ! Hi.isEditMode ) { return false; }

	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: singlePointerEvent.start.x,
	    y: singlePointerEvent.start.y,
	};
	
	if ( gSvgIconActionEditData ) {
	    if ( Hi.DEBUG ) { console.log( `Pointer down [${MODULE_NAME}]`, singlePointerEvent ); }
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionEditData.isScaling = true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionEditData.isRotating = true;
	    }
	    return true;
	} else {
	    const enclosingSvgGroup = $(singlePointerEvent.start.event.target).closest('g');
	    if ( enclosingSvgGroup.length > 0 ) {
		const svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
		if ( svgDataType == Hi.DATA_TYPE_ICON_VALUE ) {

		    if ( $(enclosingSvgGroup).attr('id') != $(gSelectedIconSvgGroup).attr('id')) {
			clearSelectedIconSvgGroup();
			gSelectedIconSvgGroup = enclosingSvgGroup[0];
		    }
		
		    if ( Hi.DEBUG ) { console.log( `Pointer down [${MODULE_NAME}]`, singlePointerEvent ); }
		    startDrag( singlePointerEvent, enclosingSvgGroup );
		    return true;
		}
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Pointer down skipped [${MODULE_NAME}]` ); }
	return false;
    }
    
    function _handleSinglePointerEventMove( singlePointerEvent ) {
	if ( ! Hi.isEditMode ) { return false; }
	
	const currentMousePosition = {
	    x: singlePointerEvent.last.x,
	    y: singlePointerEvent.last.y
	};

	let handled = false;
	
	 if ( gSvgIconActionEditData ) {
	    if ( gSvgIconActionEditData.isScaling ) {
		updateScaleFromMouseMove( currentMousePosition );
		handled = true;
	    } else if ( gSvgIconActionEditData.isRotating ) {
		updateRotateFromMouseMove( currentMousePosition );
		handled = true;
	    }
	}

	if ( gSvgIconDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gSvgIconDragData.isDragging
		 || ( distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS )
		 || ( distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS )) {
		gSvgIconDragData.isDragging = true;
		$(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, SvgActionStateType.MOVE);
		updateDrag( singlePointerEvent );
		handled = true;
	    }
	}

	gLastMousePosition = currentMousePosition;
	
	return handled;
    }
    
    function _handleSinglePointerEventEnd( singlePointerEvent ) {
	if ( ! Hi.isEditMode ) { return false; }

	let handled = endSinglePointerEvent();
	if ( handled ) {
	    if ( Hi.DEBUG ) { console.log( `Pointer end [${MODULE_NAME}]`, singlePointerEvent ); }
	} else {
	    if ( Hi.DEBUG ) { console.log( `Pointer end skipped [${MODULE_NAME}]` ); }
	}
	return handled;
    }

    function endSinglePointerEvent() {

	if ( gSvgIconActionEditData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionEditData.isScaling = false;
		endScale();
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionEditData.isRotating = false;
		endRotate();
	    }
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '');
	    gSvgIconActionEditData = null;
	    gIgnoreCLick = true;
	    return true;
	}
	
	if ( gSvgIconDragData ) {
	    if ( gSvgIconDragData.isDragging ) {
		endDrag();
		$(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '');
	    }
	    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
	    gSvgIconDragData = null;
	    return true;
	}
	
	if ( Hi.DEBUG ) { console.log( `Pointer end skipped [${MODULE_NAME}]` ); }
	return false;
    }
    
    function _handleDoublePointerEventStart( doublePointerEvent ) {
	if ( ! Hi.isEditMode ) { return false; }
	if ( ! gSelectedIconSvgGroup ) { return false; }
	endSinglePointerEvent();
	return true;
    }
    

    function _handleDoublePointerEventMove( doublePointerEvent ) {
	if ( ! Hi.isEditMode ) { return false; }
	if ( ! gSelectedIconSvgGroup ) { return false; }
	
	let scaleMultiplier = ( 1.0 + ( doublePointerEvent.deltaDistancePrevious
					/ POINTER_EVENTS_SCALE_FACTOR ));
	let deltaAngle = doublePointerEvent.deltaAngleStart * POINTER_EVENTS_ROTATE_FACTOR;

	updateScale( gSelectedIconSvgGroup, scaleMultiplier );
	updateRotate( gSelectedIconSvgGroup, deltaAngle );
	return true;
    }
    

    function _handleDoublePointerEventEnd( doublePointerEvent ) {
	let handled = endDoublePointerEvent();
	if ( handled ) {
	    if ( Hi.DEBUG ) { console.log( `Touch-2 end: [${MODULE_NAME}]`, event ); }
	} else {
	    if ( Hi.DEBUG ) { console.log( `Touch-2 end skipped: [${MODULE_NAME}]`, event ); }
	}
	return handled;
    }
    
    function endDoublePointerEvent() {
	if ( ! Hi.isEditMode ) { return false; }
	if ( ! gSelectedIconSvgGroup ) { return false; }
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
	return true;
    }
    
    function _handleMouseWheel( event ) {
	if ( ! Hi.isEditMode ) { return false; }

	if ( gSvgIconDragData ) {
	    return false;
	}

	if ( gSvgIconActionEditData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		updateScaleFromMouseWheel( event );
		event.preventDefault(); 
		event.stopImmediatePropagation();
		return true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		updateRotateFromMouseWheel( event );
		event.preventDefault(); 
		event.stopImmediatePropagation();
		return true;
	    }
	}
	return false;
    }
    
    function _handleClick( event ) {
	if ( gIgnoreCLick ) {
	    if ( Hi.DEBUG ) { console.log( `Ignoring click [${MODULE_NAME}]`, event ); }
	    gIgnoreCLick = false;
	    event.preventDefault();
	    event.stopImmediatePropagation();
	    return true;
	}
	gIgnoreCLick = false;

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length > 0 ) {
	    let svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
	    const isSvgIcon = ( svgDataType == Hi.DATA_TYPE_ICON_VALUE );
	    const svgItemId = enclosingSvgGroup.attr('id');
	    if ( isSvgIcon && svgItemId ) {
		console.log( `Click [${MODULE_NAME}]`, event );
		if ( Hi.DEBUG ) { console.log( 'SVG Target Element', enclosingSvgGroup ); }
		handleSvgIconClick( event, enclosingSvgGroup );
		event.preventDefault(); 
		event.stopImmediatePropagation();
		return true;
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Click skipped [${MODULE_NAME}]` ); }
	return false;
    }

    function _handleKeyDown( event ) {
	if ( ! Hi.isEditMode ) { return false; }

	if ( $(event.target).is('input, textarea') ) {
            return false;
	}
	if ($(event.target).closest('.modal').length > 0) {
            return false;
	}
	if ( gSelectedIconSvgGroup ) {
	    const targetArea = $(Hi.LOCATION_VIEW_AREA_SELECTOR);
            const targetOffset = targetArea.offset();
            const targetWidth = targetArea.outerWidth();
            const targetHeight = targetArea.outerHeight();
	
            if (( gLastMousePosition.x >= targetOffset.left )
		&& ( gLastMousePosition.x <= ( targetOffset.left + targetWidth ))
		&& ( gLastMousePosition.y >= targetOffset.top )
		&& ( gLastMousePosition.y <= ( targetOffset.top + targetHeight ))) {

		if ( Hi.DEBUG ) { console.log( `Key Down [${MODULE_NAME}]`, event ); }

		if ( event.key == ICON_ACTION_SCALE_KEY ) {
		    rotateAbort();
		    startScale();
		    
		} else if ( event.key == ICON_ACTION_ROTATE_KEY ) {
		    scaleAbort();
		    startRotate();
		    
		} else if ( event.key == ICON_ACTION_ZOOM_IN_KEY ) {
		    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
			scaleUpFromKeypress();
		    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
			rotateRightFromKeypress();
		    }
		    
		} else if ( event.key == ICON_ACTION_ZOOM_OUT_KEY ) {
		    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
			scaleDownFromKeypress();
		    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
			rotateLeftFromKeypress();
		    }
		    
		} else if ( event.key == 'Escape' ) {
		    scaleAbort();
		    rotateAbort();
		    gSvgIconActionState = SvgActionStateType.MOVE;
		    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '');
		    clearSelectedIconSvgGroup();
		}
	    }
	    event.preventDefault();   		
	    event.stopImmediatePropagation();
	    return true;
	}
	if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
	return false;
    }

    function handleSvgIconClick( event, enclosingSvgGroup ) {
	const svgItemId = $(enclosingSvgGroup).attr('id');

	if ( Hi.isEditMode ) {
	    clearSelectedIconSvgGroup();
	    gSelectedIconSvgGroup = $(enclosingSvgGroup)[0];
            $(enclosingSvgGroup).addClass( Hi.HIGHLIGHTED_CLASS );
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    let data = {
		moduleName: MODULE_NAME,
	    };
	    Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, data );
            AN.get( `${Hi.API_LOCATION_ITEM_DETAILS_URL}/${svgItemId}` );

	} else {
            AN.get( `${Hi.API_LOCATION_ITEM_INFO_URL}/${svgItemId}` );
	}
    }
    
    function clearSelectedIconSvgGroup() {
	if ( gSelectedIconSvgGroup ) {
            if ( Hi.DEBUG ) { console.log('Clearing svg icon selection'); }
	    $( SELECTABLE_SELECTOR ).removeClass( Hi.HIGHLIGHTED_CLASS );
	    gSelectedIconSvgGroup = null;
	}
    }

    function startDrag( singlePointerEvent, enclosingSvgGroup ) {	

	const dragElement = enclosingSvgGroup;
        Hi.displayElementInfo( 'Drag Element', dragElement );
	
	const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
	Hi.displayElementInfo( 'Base SVG', baseSvgElement );

        let transform = $(dragElement).attr('transform') || '';
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );
        let cursorSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement,
						     singlePointerEvent.last.x,
						     singlePointerEvent.last.y );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	};

	gSvgIconDragData = {
	    element: dragElement,
	    baseSvgElement: baseSvgElement,
	    cursorSvgOffset: cursorSvgOffset,
	    originalSvgScale: scale,
	    originalSvgRotate: rotate,
	    isDragging: false
	};
	
	if ( Hi.DEBUG ) {
	    console.log( `Drag Start:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ), 
    SVG Cursor Offset: ( ${gSvgIconDragData.cursorSvgOffset.x}, ${gSvgIconDragData.cursorSvgOffset.y} )`); 
	}
	
    }
    
    function updateDrag( singlePointerEvent ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
        Hi.displayEventInfo( 'Update Drag', singlePointerEvent );
        Hi.displayElementInfo( 'Drag Element', gSvgIconDragData.element );

        let cursorSvgPoint = Hi.svgUtils.toSvgPoint( gSvgIconDragData.baseSvgElement,
						     singlePointerEvent.last.x,
						     singlePointerEvent.last.y );

	let scale = gSvgIconDragData.originalSvgScale;
	let rotate = gSvgIconDragData.originalSvgRotate;
	let translate = {
	    x: (cursorSvgPoint.x / scale.x) - gSvgIconDragData.cursorSvgOffset.x,
	    y: (cursorSvgPoint.y / scale.y) - gSvgIconDragData.cursorSvgOffset.y
	};

	setSvgTransformAttr( gSvgIconDragData.element, scale, translate, rotate );
    }
    
    function endDrag() {
        if ( gSvgIconDragData == null ) {
	    return;
	}
	
        Hi.displayElementInfo( 'End Drag Element', gSvgIconDragData.element );
	saveIconSvgPositionDebouncer( gSvgIconDragData.element );
	gSvgIconDragData = null;
    }
 
    function startIconAction( actionState ) {
	if ( gSelectedIconSvgGroup ) {
            let transform = $(gSelectedIconSvgGroup).attr('transform');
            let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

	    gSvgIconActionEditData = {
		element: gSelectedIconSvgGroup,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gSvgIconActionState = actionState;
	    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, actionState );
	}
    }

    function endIconAction( element ) {
	if ( gSvgIconActionEditData ) {
	    gSvgIconActionEditData = null;
	}
    }

    function startScale() {
	startIconAction( SvgActionStateType.SCALE );	
    }

    function updateScaleFromMouseWheel( event ) {
	const e = event.originalEvent;
	let scaleMultiplier = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	if ( e.deltaY > 0 ) {
	    scaleMultiplier = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	}
	console.log( `Scale multiplier = ${scaleMultiplier} [${gSvgIconActionEditData.isScaling}]` );
	updateScale( gSvgIconActionEditData.element, scaleMultiplier );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }
    
    function scaleUpFromKeypress() {
	if ( gSelectedIconSvgGroup ) {
	    let scaleMultiplier = 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	    updateScale( gSelectedIconSvgGroup, scaleMultiplier );
	    saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
	}
    }
    
    function scaleDownFromKeypress() {
	if ( gSelectedIconSvgGroup ) {
	    let scaleMultiplier = 1.0 - ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	    updateScale( gSelectedIconSvgGroup, scaleMultiplier );
	    saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
	}
    }
    
    function updateScaleFromMouseMove( currentMousePosition ) {
	if ( Hi.DEBUG ) { console.log( `updateScale [${MODULE_NAME}]` ); }

	let center = Hi.getScreenCenterPoint( gSvgIconActionEditData.element );
	const startX = gLastMousePosition.x;
	const startY = gLastMousePosition.y;
	const endX = currentMousePosition.x;
	const endY = currentMousePosition.y;
	const startDistance = Math.sqrt( Math.pow(startX - center.x, 2) + Math.pow(startY - center.y, 2) );
	const endDistance = Math.sqrt( Math.pow(endX - center.x, 2) + Math.pow(endY - center.y, 2) );
	const moveDistance = Math.abs( endDistance - startDistance );

	let scaleMultiplier = 1.0;
	if ( endDistance > startDistance ) {
	    scaleMultiplier = 2 ** ( moveDistance / MOUSE_MOVE_ZOOM_SCALE_FACTOR );
	} else {
	    scaleMultiplier = 2 ** ( -1.0 * moveDistance / MOUSE_MOVE_ZOOM_SCALE_FACTOR );
	}
	
	if ( Hi.DEBUG ) {
	    console.log( `Scale: moveDistance=${moveDistance}, multiplier=${scaleMultiplier}` );
	}
	updateScale( gSvgIconActionEditData.element, scaleMultiplier );
	return;
    }

    function updateScale( svgIconElement, scaleMultiplier ) {
        let transformStr = $(svgIconElement).attr('transform');
	const oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );
	const newScale = {
	    x: oldTransform.scale.x * scaleMultiplier,
	    y: oldTransform.scale.y * scaleMultiplier
	};
	const newTranslate = {
	    x: oldTransform.translate.x * oldTransform.scale.x / newScale.x,
	    y: oldTransform.translate.y * oldTransform.scale.y / newScale.y
	};
	
	if ( Hi.DEBUG ) {
	    console.log( `Scale Update:
Original (str):  ${transformStr}
  Old (parsed):  ${JSON.stringify(oldTransform)}
    Multiplier:  ${scaleMultiplier}
           New:  S = ${JSON.stringify(newScale)}, T = ${JSON.stringify(newTranslate)}, R = ${JSON.stringify(oldTransform.rotate)}` );
	}

	setSvgTransformAttr( svgIconElement, newScale, newTranslate, oldTransform.rotate );
    }
    
    function endScale() {
	if ( Hi.DEBUG ) { console.log( 'Scale End' ); }
	saveIconSvgPosition( gSvgIconActionEditData.element );
    }

    function scaleAbort() {
	if ( gSvgIconActionState != SvgActionStateType.SCALE ) {
	    return;
	}
	endIconAction();
    }

    function startRotate() {
	startIconAction( SvgActionStateType.ROTATE );	
    }

    function updateRotateFromMouseMove( currentMousePosition ) {
	if ( Hi.DEBUG ) { console.log( `updateRotation [${MODULE_NAME}]` ); }

	let center = Hi.getScreenCenterPoint( gSvgIconActionEditData.element );

	let deltaAngle = Hi.getRotationAngle( center.x, center.y,
					      gLastMousePosition.x, gLastMousePosition.y,
					      currentMousePosition.x, currentMousePosition.y );
	
        let transformStr = $(gSvgIconActionEditData.element).attr('transform');
 	const oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );

	const newRotate = { ...oldTransform.rotate }; // Create a copy of old values
	newRotate.angle += deltaAngle;
	newRotate.angle = Hi.normalizeAngle( newRotate.angle );

	setSvgTransformAttr( gSvgIconActionEditData.element,
			     oldTransform.scale, oldTransform.translate, newRotate );
    }

    function updateRotateFromMouseWheel( event ) {
	const e = event.originalEvent;
	let deltaAngle = MOUSE_WHEEL_ROTATE_DEGREES;
	if ( e.deltaY > 0 ) {
	    deltaAngle = -1.0 * MOUSE_WHEEL_ROTATE_DEGREES;
	}
	updateRotate( gSvgIconActionEditData.element, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }
    
    function rotateRightFromKeypress() {
	let deltaAngle = KEYPRESS_ROTATE_DEGREES;
	updateRotate( gSelectedIconSvgGroup, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }

    function rotateLeftFromKeypress() {
	let deltaAngle = -1.0 * KEYPRESS_ROTATE_DEGREES;
	updateRotate( gSelectedIconSvgGroup, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }

    function updateRotate( svgIconElement, deltaAngle ) {
        let transformStr = $(svgIconElement).attr('transform');
 	const oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );

	const newRotate = { ...oldTransform.rotate }; // Create a copy of old values
	newRotate.angle += deltaAngle;
	newRotate.angle = Hi.normalizeAngle( newRotate.angle );
	
	if ( Hi.DEBUG ) {
	    console.log( `Rotate Update:
Original (str):  ${transformStr}
  Old (parsed):  ${JSON.stringify(oldTransform)}
   Angle Delta:  ${deltaAngle}
           New:  S = ${JSON.stringify(oldTransform.scale)}, T = ${JSON.stringify(oldTransform.translate)}, R = ${JSON.stringify(newRotate)}` );
	}
	
	setSvgTransformAttr( svgIconElement,
			     oldTransform.scale, oldTransform.translate, newRotate );
    }
    
    function endRotate() {
	saveIconSvgPosition( gSvgIconActionEditData.element );
    }
    
    function rotateAbort() {
	if ( gSvgIconActionState != SvgActionStateType.ROTATE ) {
	    return;
	}	
	endIconAction();
    }

    function setSvgTransformAttr( element, scale, translate, rotate ) {
        let newTransform = `scale(${scale.x} ${scale.y}) translate(${translate.x}, ${translate.y}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        $(element).attr('transform', newTransform);	    
    }

    function saveIconSvgPositionDebouncer( element ) {
        const currentTime = Date.now();
        const timeSinceLastApiCall = currentTime - lastPositionApiCallTime;

        clearTimeout( positionApiCallDebounceTimer );
        positionApiCallDebounceTimer = setTimeout(() => {
	    saveIconSvgPosition( element );
            lastPositionApiCallTime = Date.now();
        }, POSITION_API_CALL_DEBOUNCE_MS );
    }
    
    function saveIconSvgPosition( element ) {

        let transform = $(element).attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

	const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
	const center = Hi.svgUtils.getSvgCenterPoint( element, baseSvgElement );

	let svgItemId = $(element).attr('id');
	let data = {
	    svg_x: center.x,
	    svg_y: center.y,
	    svg_scale: scale.x,
	    svg_rotate: rotate.angle,
	};
	AN.post( `${API_EDIT_LOCATION_ITEM_POSITION_URL}/${svgItemId}`, data );
    }

    
})();
