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
	handlePointerDown: function( pointerEventData ) {
	    return _handlePointerDown( pointerEventData );	    
	},
	handlePointerMove: function( pointerEventData ) {
	    return _handlePointerMove( pointerEventData );	    
	},
	handlePointerUp: function( pointerEventData ) {
	    return _handlePointerUp( pointerEventData );	    
	},
	scaleAndRotateFromPointerEvents: function( pointerEventData ) {
	    return _scaleAndRotateFromPointerEvents( pointerEventData );	    
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
    
    function _handlePointerDown( pointerEventData ) {
	if ( ! Hi.isEditMode ) { return false; }

	const event = pointerEventData.start.event;
	
	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	};
	
	if ( gSvgIconActionEditData ) {
	    if ( Hi.DEBUG ) { console.log( `Pointer down event [${MODULE_NAME}]`, event ); }
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionEditData.isScaling = true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionEditData.isRotating = true;
	    }
	    return true;
	} else {
	    const enclosingSvgGroup = $(event.target).closest('g');
	    if ( enclosingSvgGroup.length > 0 ) {
		const svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
		if ( svgDataType == Hi.DATA_TYPE_ICON_VALUE ) {

		    if ( $(enclosingSvgGroup).attr('id') != $(gSelectedIconSvgGroup).attr('id')) {
			clearSelectedIconSvgGroup();
			gSelectedIconSvgGroup = enclosingSvgGroup;
		    }
		
		    if ( Hi.DEBUG ) { console.log( `Pointer down event [${MODULE_NAME}]`, event ); }
		    createIconDragData( event, enclosingSvgGroup );
		    return true;
		}
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Pointer down skipped [${MODULE_NAME}]` ); }
	return false;
    }
    
    function _handlePointerMove( pointerEventData ) {
	if ( ! Hi.isEditMode ) { return false; }

	const event = pointerEventData.last.event;
	
	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};

	let handled = false;
	
	 if ( gSvgIconActionEditData ) {
	    if ( gSvgIconActionEditData.isScaling ) {
		iconActionScaleFromMouseMove( currentMousePosition );
		handled = true;
	    } else if ( gSvgIconActionEditData.isRotating ) {
		iconActionRotateUpdateFromMouseMove( currentMousePosition );
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
		updateDrag(event);
		handled = true;
	    }
	}

	gLastMousePosition = currentMousePosition;
	
	return handled;
    }
    
    function _handlePointerUp( pointerEventData ) {
	if ( ! Hi.isEditMode ) { return false; }

	const event = pointerEventData.last.event;

	if ( gSvgIconActionEditData ) {
	    if ( Hi.DEBUG ) { console.log( `Pointer up event [${MODULE_NAME}]`, event ); }
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionEditData.isScaling = false;
		iconActionScaleApply();
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionEditData.isRotating = false;
		iconActionRotateApply();
	    }
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '');
	    gSvgIconActionEditData = null;
	    gIgnoreCLick = true;
	    return true;
	}
	
	if ( gSvgIconDragData ) {
	    if ( Hi.DEBUG ) { console.log( `Pointer up event [${MODULE_NAME}]`, event ); }
	    if ( gSvgIconDragData.isDragging ) {
		applyDrag( event );
		$(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '');
	    }
	    $(Hi.BASE_SVG_SELECTOR).attr( Hi.SVG_ACTION_STATE_ATTR_NAME, '' );
	    gSvgIconDragData = null;
	    return true;
	}
	
	if ( Hi.DEBUG ) { console.log( `Pointer up skipped [${MODULE_NAME}]` ); }
	return false;
    }

    function _handleMouseWheel( event ) {
	if ( ! Hi.isEditMode ) { return false; }

	if ( gSvgIconDragData ) {
	    return false;
	}

	if ( gSvgIconActionEditData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		iconActionScaleFromMouseWheel( event );
		event.preventDefault(); 
		event.stopImmediatePropagation();
		return true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		iconActionRotateFromMouseWheel( event );
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
		    iconActionRotateAbort();
		    iconActionScaleStart();
		    
		} else if ( event.key == ICON_ACTION_ROTATE_KEY ) {
		    iconActionScaleAbort();
		    iconActionRotateStart();
		    
		} else if ( event.key == ICON_ACTION_ZOOM_IN_KEY ) {
		    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
			iconActionScaleUpFromKeypress();
		    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
			iconActionRotateRightFromKeypress();
		    }
		    
		} else if ( event.key == ICON_ACTION_ZOOM_OUT_KEY ) {
		    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
			iconActionScaleDownFromKeypress();
		    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
			iconActionRotateLeftFromKeypress();
		    }
		    
		} else if ( event.key == 'Escape' ) {
		    iconActionScaleAbort();
		    iconActionRotateAbort();
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
	    gSelectedIconSvgGroup = enclosingSvgGroup;
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

    function createIconDragData( event, enclosingSvgGroup ) {	

	const dragElement = enclosingSvgGroup;
        Hi.displayElementInfo( 'Drag Element', dragElement );
	
	const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
	Hi.displayElementInfo( 'Base SVG', baseSvgElement );

        let transform = dragElement.attr('transform') || '';
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );
        let cursorSvgPoint = Hi.svgUtils.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	};

	gSvgIconDragData = {
	    element: dragElement,
	    baseSvgElement: baseSvgElement,
	    cursorSvgOffset: cursorSvgOffset,
	    elementSvgCenterPoint: Hi.svgUtils.getSvgCenterPoint( dragElement, baseSvgElement ),
	    originalSvgScale: scale,
	    originalSvgRotate: rotate,
	    isDragging: false
	};
	
	if ( Hi.DEBUG ) {
	    console.log( `Drag Start:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ), 
    SVG Cursor Offset: ( ${gSvgIconDragData.cursorSvgOffset.x}, ${gSvgIconDragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
        Hi.displayEventInfo( 'Update Drag', event );
        Hi.displayElementInfo( 'Drag Element', gSvgIconDragData.element );

        let cursorSvgPoint = Hi.svgUtils.toSvgPoint( gSvgIconDragData.baseSvgElement,
						     event.clientX,
						     event.clientY );

	let scale = gSvgIconDragData.originalSvgScale;
	let rotate = gSvgIconDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gSvgIconDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gSvgIconDragData.cursorSvgOffset.y;

        let transform = gSvgIconDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gSvgIconDragData.element.attr('transform', newTransform);	    

	gSvgIconDragData.elementSvgCenterPoint = Hi.svgUtils.getSvgCenterPoint(
	    gSvgIconDragData.element,
	    gSvgIconDragData.baseSvgElement );
	
	if ( Hi.DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function applyDrag( event ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
	
        Hi.displayEventInfo( 'End Drag', event );
        Hi.displayElementInfo( 'Drag Element', gSvgIconDragData.element );
	updateDrag( event );

	let svgItemId = gSvgIconDragData.element.attr('id');
	let data = {
	    svg_x: gSvgIconDragData.elementSvgCenterPoint.x,
	    svg_y: gSvgIconDragData.elementSvgCenterPoint.y,
	    svg_scale: gSvgIconDragData.originalSvgScale.x,
	    svg_rotate: gSvgIconDragData.originalSvgRotate.angle
	};

	if ( Hi.DEBUG ) { console.log( 'Applying Drag:', data ); }
	AN.post( `${API_EDIT_LOCATION_ITEM_POSITION_URL}/${svgItemId}`, data );

	gSvgIconDragData = null;
    }
 
    function createIconActionEditData( actionState ) {
	if ( gSelectedIconSvgGroup ) {
            let transform = gSelectedIconSvgGroup.attr('transform');
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

    function abortIconAction( element ) {
	if ( gSvgIconActionEditData ) {
	    gSvgIconActionEditData = null;
	}
    }

    function iconActionScaleStart() {
	createIconActionEditData( SvgActionStateType.SCALE );	
    }

    function iconActionScaleApply() {
	if ( Hi.DEBUG ) { console.log( 'Scale Apply' ); }
	saveIconSvgPosition( gSvgIconActionEditData.element );
    }

    function iconActionScaleAbort() {
	if ( gSvgIconActionState != SvgActionStateType.SCALE ) {
	    return;
	}
	abortIconAction();
    }

    function iconActionScaleFromMouseWheel( event ) {
	const e = event.originalEvent;
	let scaleMultiplier = 1.0 + ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	if ( e.deltaY > 0 ) {
	    scaleMultiplier = 1.0 - ( MOUSE_WHEEL_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	}
	console.log( `Scale multiplier = ${scaleMultiplier} [${gSvgIconActionEditData.isScaling}]` );
	adjustIconScale( gSvgIconActionEditData.element, scaleMultiplier );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }
    
    function iconActionScaleUpFromKeypress() {
	if ( gSelectedIconSvgGroup ) {
	    let scaleMultiplier = 1.0 + ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	    adjustIconScale( gSelectedIconSvgGroup, scaleMultiplier );
	    saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
	}
    }
    
    function iconActionScaleDownFromKeypress() {
	if ( gSelectedIconSvgGroup ) {
	    let scaleMultiplier = 1.0 - ( KEYPRESS_ZOOM_SCALE_FACTOR_PERCENT / 100.0 );
	    adjustIconScale( gSelectedIconSvgGroup, scaleMultiplier );
	    saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
	}
    }
    
    function iconActionScaleFromMouseMove( currentMousePosition ) {
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
	adjustIconScale( gSvgIconActionEditData.element, scaleMultiplier );
	return;
    }

    function adjustIconScale( svgIconElement, scaleMultiplier ) {
        let transformStr = svgIconElement.attr('transform');
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
    
    function iconActionRotateStart() {
	createIconActionEditData( SvgActionStateType.ROTATE );	
    }

    function iconActionRotateUpdateFromMouseMove( currentMousePosition ) {
	if ( Hi.DEBUG ) { console.log( `updateRotation [${MODULE_NAME}]` ); }

	let center = Hi.getScreenCenterPoint( gSvgIconActionEditData.element );

	let deltaAngle = Hi.getRotationAngle( center.x, center.y,
					      gLastMousePosition.x, gLastMousePosition.y,
					      currentMousePosition.x, currentMousePosition.y );
	
        let transformStr = gSvgIconActionEditData.element.attr('transform');
 	const oldTransform = Hi.svgUtils.getSvgTransformValues( transformStr );

	const newRotate = { ...oldTransform.rotate }; // Create a copy of old values
	newRotate.angle += deltaAngle;
	newRotate.angle = Hi.normalizeAngle( newRotate.angle );

	setSvgTransformAttr( gSvgIconActionEditData.element,
			     oldTransform.scale, oldTransform.translate, newRotate );
    }

    function iconActionRotateFromMouseWheel( event ) {
	const e = event.originalEvent;
	let deltaAngle = MOUSE_WHEEL_ROTATE_DEGREES;
	if ( e.deltaY > 0 ) {
	    deltaAngle = -1.0 * MOUSE_WHEEL_ROTATE_DEGREES;
	}
	adjustIconRotate( gSvgIconActionEditData.element, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }
    
    function iconActionRotateRightFromKeypress() {
	let deltaAngle = KEYPRESS_ROTATE_DEGREES;
	adjustIconRotate( gSelectedIconSvgGroup, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }

    function iconActionRotateLeftFromKeypress() {
	let deltaAngle = -1.0 * KEYPRESS_ROTATE_DEGREES;
	adjustIconRotate( gSelectedIconSvgGroup, deltaAngle );
	saveIconSvgPositionDebouncer( gSelectedIconSvgGroup );
    }

    function adjustIconRotate( svgIconElement, deltaAngle ) {
        let transformStr = svgIconElement.attr('transform');
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
    
    function iconActionRotateApply() {
	saveIconSvgPosition( gSvgIconActionEditData.element );
    }
    
    function iconActionRotateAbort() {
	if ( gSvgIconActionState != SvgActionStateType.ROTATE ) {
	    return;
	}	
	abortIconAction();
    }

    function _scaleAndRotateFromPointerEvents( pointerEventData ) {
	if ( gSvgIconActionEditData ) {








	}
	return false;
    }
    

    function setSvgTransformAttr( element, scale, translate, rotate ) {
        let newTransform = `scale(${scale.x} ${scale.y}) translate(${translate.x}, ${translate.y}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        element.attr('transform', newTransform);	    
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

        let transform = element.attr('transform');
        let { scale, translate, rotate } = Hi.svgUtils.getSvgTransformValues( transform );

	const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
	const center = Hi.svgUtils.getSvgCenterPoint( element, baseSvgElement );

	let svgItemId = element.attr('id');
	let data = {
	    svg_x: center.x,
	    svg_y: center.y,
	    svg_scale: scale.x,
	    svg_rotate: rotate.angle,
	};
	AN.post( `${API_EDIT_LOCATION_ITEM_POSITION_URL}/${svgItemId}`, data );
    }

    
})();
