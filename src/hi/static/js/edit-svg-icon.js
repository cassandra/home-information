(function() {

    window.Hi = window.Hi || {};
    window.Hi.edit = window.Hi.edit || {};

    const MODULE_NAME = 'svg-icon';    

    const HiEditSvgIcon = {
        init: function() {
            Hi.edit.eventBus.subscribe( Hi.edit.SELECTION_MADE_EVENT_NAME,
					this.clearSelection.bind(this) );
        },
        clearSelection: function( data ) {
	    if ( data != MODULE_NAME ) {
		clearSelectedIconSvgGroup();
            }
        }	
    };

    window.Hi.edit.icon = HiEditSvgIcon;
    HiEditSvgIcon.init();

    /* 
      SVG ICON EDITING
      
      - Icons can be selected to show the entity details in the side edit panel.
      - Icons can be dragged to chnage their location.
      - Selected icons can be rotated and scaled to change their appearance.
    */
    
    const SELECTABLE_CLASS = 'selectable';
    const SELECTABLE_SELECTOR = '.' + SELECTABLE_CLASS;
    
    const ICON_ACTION_STATE_ATTR_NAME = 'action-state';
    const ICON_ACTION_SCALE_KEY = 's';
    const ICON_ACTION_ROTATE_KEY = 'r';

    const CLICK_HOLD_THRESHOLD_MS = 50; // For ignoreing very short, transient clicks
    const DOUBLE_CLICK_DELAY_MS = 250;
    const CURSOR_MOVEMENT_THRESHOLD_PIXELS = 3;

    const API_EDIT_SVG_POSITION_URL = '/edit/svg/position';
        
    const SvgActionStateType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };
    
    let gSvgIconActionState = SvgActionStateType.MOVE;
    let gSelectedIconSvgGroup = null;
    let gSvgIconDragData = null;
    let gSvgIconEditData = null;

    let gClickStart = null;
    let gClickTimeout = null;
    let gLastMousePosition = { x: 0, y: 0 };
    let gIgnoreCLick = false;  // Set by mouseup handling when non-click actions are needed
    
    
    $(document).ready(function() {

	$(document).on('mousedown', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseDown( event );
	});
	$(document).on('mousemove', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseMove( event );
	});
	$(document).on('mouseup', Hi.LOCATION_VIEW_AREA_SELECTOR, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseUp( event );
	});
	$(document).on('click', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleClick( event );
	});
	$(document).on('keydown', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleKeyDown( event );
	});
    });

    function handleMouseDown( event ) {
	if ( Hi.DEBUG ) { Hi.displayEventInfo( `Mouse down event [${MODULE_NAME}]`, event ); }

	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	    time: Date.now()
	};
	
	if ( gSvgIconEditData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconEditData.isScaling = true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconEditData.isRotating = true;
	    }
	    event.preventDefault();
	    return;
	} else {
            if ( Hi.DEBUG ) { Hi.displayElementInfo( 'Event target: ', $(event.target) ); }
	    const enclosingSvgGroup = $(event.target).closest('g');
	    if ( enclosingSvgGroup.length > 0 ) {
		const svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
		if ( svgDataType == Hi.DATA_TYPE_ICON_VALUE ) {
		    createIconDragData( event, enclosingSvgGroup );
		    event.preventDefault();
		    return;
		}
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Mouse down skipped [${MODULE_NAME}]` ); }
    }
    
    function handleMouseUp( event ) {
	if ( Hi.DEBUG ) { Hi.displayEventInfo( `Mouse up event [${MODULE_NAME}]`, event ); }
	
	if ( gSvgIconDragData ) {
	    if ( gSvgIconDragData.isDragging ) {
		endDrag( event );
		$(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
	    }
	    $(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '' );
	    gSvgIconDragData = null;
	    event.preventDefault(); 
	    return;
	}
	
	else if ( gSvgIconEditData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconEditData.isScaling = false;
		iconActionScaleApply();
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconEditData.isRotating = false;
		iconActionRotateApply();
	    }
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    $(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
	    gSvgIconEditData = null;
	    gIgnoreCLick = true;
	    event.preventDefault(); 
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Mouse up skipped [${MODULE_NAME}]` ); }
    }
    
    function handleMouseMove( event ) {

	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	
	if ( gSvgIconDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gSvgIconDragData.isDragging
		 || ( distanceX > CURSOR_MOVEMENT_THRESHOLD_PIXELS )
		 || ( distanceY > CURSOR_MOVEMENT_THRESHOLD_PIXELS )) {
		gSvgIconDragData.isDragging = true;
		$(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, SvgActionStateType.MOVE);
		updateDrag(event);
		event.preventDefault(); 
	    }
	}
	else if ( gSvgIconEditData ) {
	    if ( gSvgIconEditData.isScaling ) {
		iconActionScaleUpdate( currentMousePosition );
		event.preventDefault(); 
	    } else if ( gSvgIconEditData.isRotating ) {
		iconActionRotateUpdate( currentMousePosition );
		event.preventDefault(); 
	    }
	}
	
	gLastMousePosition = currentMousePosition;
    }
    
    function handleClick( event ) {
	if ( gIgnoreCLick ) {
	    if ( Hi.DEBUG ) { console.log( `Ignoring click [${MODULE_NAME}]`, event ); }
	    gIgnoreCLick = false;
	    event.preventDefault(); 
	    return;
	}
	gIgnoreCLick = false;

	if ( Hi.DEBUG ) {
            console.log( `Click [${MODULE_NAME}]`, event );
            Hi.displayElementInfo( 'Event Target', $(event.target) );
	}
	
	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length > 0 ) {
            if ( Hi.DEBUG ) { console.log( 'SVG Target Element', enclosingSvgGroup ); }
	    let svgDataType = $(enclosingSvgGroup).attr( Hi.DATA_TYPE_ATTR );
	    const isSvgIcon = ( svgDataType == Hi.DATA_TYPE_ICON_VALUE );
	    const svgItemId = enclosingSvgGroup.attr('id');
	    if ( isSvgIcon && svgItemId ) {
		handleSvgIconClick( event, enclosingSvgGroup );
		event.preventDefault(); 
		return;
	    }
	}
	if ( Hi.DEBUG ) { console.log( `Click skipped [${MODULE_NAME}]` ); }
    }

    function handleKeyDown( event ) {
	if ( $(event.target).is('input[type="text"], textarea') ) {
            return;
	}
	if ( gSelectedIconSvgGroup ) {
	    handleSvgIconSelectedKeyDown( event );
	    event.preventDefault();
	    return;
	}
	if ( Hi.DEBUG ) { console.log( `Key down skipped [${MODULE_NAME}]` ); }
    }

    function handleSvgIconSelectedKeyDown( event ) {
	const targetArea = $(Hi.LOCATION_VIEW_AREA_SELECTOR);
        const targetOffset = targetArea.offset();
        const targetWidth = targetArea.outerWidth();
        const targetHeight = targetArea.outerHeight();
	
        if (gLastMousePosition.x >= targetOffset.left && 
	    gLastMousePosition.x <= targetOffset.left + targetWidth &&
	    gLastMousePosition.y >= targetOffset.top &&
	    gLastMousePosition.y <= targetOffset.top + targetHeight) {

       	    if ( Hi.DEBUG ) { Hi.displayEventInfo( 'Key Down', event ); }

	    if ( event.key == ICON_ACTION_SCALE_KEY ) {
		iconActionRotateAbort();
		iconActionScaleStart();
		
	    } else if ( event.key == ICON_ACTION_ROTATE_KEY ) {
		iconActionScaleAbort();
		iconActionRotateStart();
		
	    } else if ( event.key == 'Escape' ) {
		iconActionScaleAbort();
		iconActionRotateAbort();
		gSvgIconActionState = SvgActionStateType.MOVE;
		$(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, '');
		
	    } else {
		return;
	    }
	
	    event.stopPropagation();
	    event.preventDefault();   		
        }
    }
    
    function handleSvgIconClick( event, enclosingSvgGroup ) {
	const svgItemId = $(enclosingSvgGroup).attr('id');
	clearSelectedIconSvgGroup();
	gSelectedIconSvgGroup = enclosingSvgGroup;
        $(enclosingSvgGroup).addClass( Hi.HIGHLIGHTED_CLASS );
	Hi.edit.eventBus.emit( Hi.edit.SELECTION_MADE_EVENT_NAME, MODULE_NAME );
        AN.get( `${Hi.API_SHOW_DETAILS_URL}/${svgItemId}` );
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
        let { scale, translate, rotate } = getSvgTransformValues( transform );
        let cursorSvgPoint = Hi.toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	};

	gSvgIconDragData = {
	    element: dragElement,
	    baseSvgElement: baseSvgElement,
	    cursorSvgOffset: cursorSvgOffset,
	    elementSvgCenterPoint: getSvgCenterPoint( dragElement, baseSvgElement ),
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

        let cursorSvgPoint = Hi.toSvgPoint( gSvgIconDragData.baseSvgElement, event.clientX, event.clientY );

	let scale = gSvgIconDragData.originalSvgScale;
	let rotate = gSvgIconDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gSvgIconDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gSvgIconDragData.cursorSvgOffset.y;

        let transform = gSvgIconDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gSvgIconDragData.element.attr('transform', newTransform);	    

	gSvgIconDragData.elementSvgCenterPoint = getSvgCenterPoint( gSvgIconDragData.element, gSvgIconDragData.baseSvgElement );
	
	if ( Hi.DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function endDrag( event ) {
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
	AN.post( `${API_EDIT_SVG_POSITION_URL}/${svgItemId}`, data );

	gSvgIconDragData = null;
    }
 
    function saveIconSvgPosition( element ) {

        let transform = element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const baseSvgElement = $(Hi.BASE_SVG_SELECTOR);
	const center = getSvgCenterPoint( element, baseSvgElement );

	let svgItemId = element.attr('id');
	let data = {
	    svg_x: center.x,
	    svg_y: center.y,
	    svg_scale: scale.x,
	    svg_rotate: rotate.angle,
	};
	AN.post( `${API_EDIT_SVG_POSITION_URL}/${svgItemId}`, data );
    }

    function createIconEditActionData( actionState ) {
	if ( gSelectedIconSvgGroup ) {
            let transform = gSelectedIconSvgGroup.attr('transform');
            let { scale, translate, rotate } = getSvgTransformValues( transform );

	    gSvgIconEditData = {
		element: gSelectedIconSvgGroup,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gSvgIconActionState = actionState;
	    $(Hi.BASE_SVG_SELECTOR).attr( ICON_ACTION_STATE_ATTR_NAME, actionState );
	}
    }

    function revertIconAction( element ) {
	if ( gSvgIconEditData ) {
	    setSvgTransformAttr( gSvgIconEditData.element,
				 gSvgIconEditData.scaleStart,
				 gSvgIconEditData.translateStart,
				 gSvgIconEditData.rotateStart );
	    gSvgIconEditData = null;
	}
    }
    
    function iconActionScaleStart() {
	createIconEditActionData( SvgActionStateType.SCALE );	
    }

    function iconActionScaleUpdate( currentMousePosition ) {

	let center = getScreenCenterPoint( gSvgIconEditData.element );

	let scaleFactor = getScaleFactor( center.x, center.y,
					  gLastMousePosition.x, gLastMousePosition.y,
					  currentMousePosition.x, currentMousePosition.y );
        let transform = gSvgIconEditData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const newScale = {
	    x: scale.x * scaleFactor,
	    y: scale.y * scaleFactor
	};
		
	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.y / newScale.y;

	if ( Hi.DEBUG ) {
	    console.log( `Scale Update:
    Transform:  ${transform}
    Scale = ${scale.x}, T = ${translate.x}, R = ${rotate.angle}` );
	}

	setSvgTransformAttr( gSvgIconEditData.element, newScale, translate, rotate );

    }

    function iconActionScaleApply() {
	if ( Hi.DEBUG ) { console.log( 'Scale Apply' ); }
	saveIconSvgPosition( gSvgIconEditData.element );
    }

    function iconActionScaleAbort() {
	if ( gSvgIconActionState != SvgActionStateType.SCALE ) {
	    return;
	}
	revertIconAction();
    }

    function iconActionRotateStart() {
	createIconEditActionData( SvgActionStateType.ROTATE );	
    }

    function iconActionRotateUpdate( currentMousePosition ) {
	if ( Hi.DEBUG ) { console.log( 'Rotate Update' ); }

	let center = getScreenCenterPoint( gSvgIconEditData.element );

	let deltaAngle = getIconRotationAngle( center.x, center.y,
					   gLastMousePosition.x, gLastMousePosition.y,
					   currentMousePosition.x, currentMousePosition.y );

        let transform = gSvgIconEditData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = normalizeAngle( rotate.angle );
	setSvgTransformAttr( gSvgIconEditData.element, scale, translate, rotate );
    }

    function getIconRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

	const startVectorX = startX - centerX;
	const startVectorY = startY - centerY;

	const endVectorX = endX - centerX;
	const endVectorY = endY - centerY;

	const startAngle = Math.atan2(startVectorY, startVectorX);
	const endAngle = Math.atan2(endVectorY, endVectorX);

	let angleDifference = endAngle - startAngle;

	// Normalize the angle to be between -π and π
	if (angleDifference > Math.PI) {
            angleDifference -= 2 * Math.PI;
	} else if (angleDifference < -Math.PI) {
            angleDifference += 2 * Math.PI;
	}

	const angleDifferenceDegrees = angleDifference * (180 / Math.PI);

	return angleDifferenceDegrees;
    }

    
    function iconActionRotateApply() {
	saveIconSvgPosition( gSvgIconEditData.element );
    }
    
    function iconActionRotateAbort() {
	if ( gSvgIconActionState != SvgActionStateType.ROTATE ) {
	    return;
	}	
	revertIconAction();
    }

    function getScreenCenterPoint( element ) {
	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return {
		    x: rect.left + ( rect.width / 2.0 ),
		    y: rect.top + ( rect.height / 2.0 )
		};
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return null;
    }
    
    function getSvgCenterPoint( element, svgElement ) {

	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return Hi.toSvgPoint( svgElement, screenCenterX, screenCenterY );
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return { x: 0, y: 0 };
    }
        
    function getSvgTransformValues(transform) {
	let scale = { x: 1, y: 1 }, rotate = { angle: 0, cx: 0, cy: 0 }, translate = { x: 0, y: 0 };

	let scaleMatch = transform.match(/scale\(([^)]+)\)/);
	if (scaleMatch) {
	    let scaleValues = scaleMatch[1].trim().split(/[ ,]+/).map(parseFloat);
	    scale.x = scaleValues[0];
	    if ( scaleValues.length == 1 ) {
		scale.y = scale.x;
	    } else {
		scale.y = scaleValues[1];
	    }
	}

	let translateMatch = transform.match(/translate\(([^)]+)\)/);
	if (translateMatch) {
            let [x, y] = translateMatch[1].trim().split(/[ ,]+/).map(parseFloat);
            translate.x = x;
            translate.y = y;
	}

	let rotateMatch = transform.match(/rotate\(([^)]+)\)/);
	if (rotateMatch) {
            let rotateValues = rotateMatch[1].trim().split(/[ ,]+/).map(parseFloat);
            rotate.angle = rotateValues[0];

            // Check if cx and cy are provided
            if (rotateValues.length === 3) {
		rotate.cx = rotateValues[1];
		rotate.cy = rotateValues[2];
            } else {
		rotate.cx = 0;
		rotate.cy = 0;
	    }
	}

	if ( Hi.DEBUG ) {
	    console.log( `TRANSFORM:
    Raw: ${transform},
    Parsed: scale=${JSON.stringify(scale)} translate=${JSON.stringify(translate)} rotate=${JSON.stringify(rotate)}` );
	}
	
	return { scale, translate, rotate };
    }

    function setSvgTransformAttr( element, scale, translate, rotate ) {
        let newTransform = `scale(${scale.x} ${scale.y}) translate(${translate.x}, ${translate.y}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;
        element.attr('transform', newTransform);	    
    }
    
    function getScaleFactor( centerX, centerY, startX, startY, endX, endY ) {

	const startDistance = Math.sqrt( Math.pow(startX - centerX, 2) + Math.pow(startY - centerY, 2) );
	const endDistance = Math.sqrt( Math.pow(endX - centerX, 2) + Math.pow(endY - centerY, 2) );

	let scaleFactor = 1;
	if (endDistance > startDistance) {
            scaleFactor = 1 + (endDistance - startDistance) / 100;
	} else if (endDistance < startDistance) {
            scaleFactor = 1 - (startDistance - endDistance) / 100;
	}
	return scaleFactor;
    }
    
    function normalizeAngle(angle) {
	return (angle % 360 + 360) % 360;
    }


    
})();
