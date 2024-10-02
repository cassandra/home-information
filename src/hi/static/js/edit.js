(function() {
    const DEBUG = true;

    window.Hi = window.Hi || {};

    const HiEdit = {
	editThing: function() {
            return true;
	}
    };
    
    window.Hi.edit = HiEdit;

    const locationViewAreaSelector = '#hi-location-view-main';
    const baseSvgSelector = '#hi-location-view-main > svg';

    const EditActionState = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };    
    const EditActionStateAttrName = 'action-state';
    const ActionMoveKey = 'm';
    const ActionScaleKey = 's';
    const ActionRotateKey = 'r';

    const DoubleClickDelayMs = 300;
    const CursorMovementThreshold = 3;
    
    let gEditActionState = EditActionState.MOVE;
    let gSelectedElement = null;

    let gClickStart = null;
    let gClickTimeout = null;
    let gLastMousePosition = { x: 0, y: 0 };

    let gDragData = null;
    let gEditActionData = null;
    
    $(document).ready(function() {
	$(document).on('mousedown', locationViewAreaSelector, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseDown( event );
	    
	});
	$(document).on('mousemove', locationViewAreaSelector, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseMove( event );
	});
	$(document).on('mouseup', locationViewAreaSelector, function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleMouseUp( event );
	});
	$(document).on('keydown', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleKeyDown( event );
	});
	$(document).on('keyup', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleKeyUp( event );
	});
    });

    function handleMouseDown( event ) {
	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	    time: Date.now()
	};
	
	if ( gEditActionState == EditActionState.MOVE ) {
	    createDragData( event );
	    return;
	} 
	if ( gEditActionData ) {
	    if ( gEditActionState == EditActionState.SCALE ) {
		gEditActionData.isScaling = true;
	    } else if ( gEditActionState == EditActionState.ROTATE ) {
		gEditActionData.isRotating = true;
	    }
	}
    }
    
    function handleMouseMove( event ) {
	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	
	if ( gDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gDragData.isDragging || ( distanceX > CursorMovementThreshold ) || ( distanceY > CursorMovementThreshold )) {
		gDragData.isDragging = true;
		$(baseSvgSelector).attr( EditActionStateAttrName, EditActionState.MOVE);
		updateDrag(event);
	    }
	}
	else if ( gEditActionData ) {
	    if ( gEditActionData.isScaling ) {
		actionScaleUpdate( currentMousePosition );
	    } else if ( gEditActionData.isRotating ) {
		actionRotateUpdate( currentMousePosition );
	    }
	}
	
	gLastMousePosition = currentMousePosition;
    }
    
    function handleMouseUp( event ) {
	if ( gDragData ) {
	    if ( gDragData.isDragging ) {
		endDrag( event );
		$(baseSvgSelector).attr( EditActionStateAttrName, '');
		return;
	    }
	    $(baseSvgSelector).attr( EditActionStateAttrName, '' );
	    gDragData = null;
	}
	
	else if ( gEditActionData ) {
	    if ( gEditActionState == EditActionState.SCALE ) {
		gEditActionData.isScaling = false;
		actionScaleApply();
	    } else if ( gEditActionState == EditActionState.ROTATE ) {
		gEditActionData.isRotating = false;
		actionRotateApply();
	    }
	    gEditActionState = EditActionState.MOVE;
	    $(baseSvgSelector).attr( EditActionStateAttrName, '');
	    gEditActionData = null;
	}
	
	if ( gClickTimeout ) {
	    const clickEndTime = Date.now();
	    const elapsedTime = clickEndTime - gClickStart.time;
	    if ( DEBUG ) { console.log( `Click Elapsed: ${elapsedTime}` ); }
	    clearTimeout( gClickTimeout );
	    gClickTimeout = null;
	    handleDoubleClick( event );
	} else {
	    gClickTimeout = setTimeout(() => {
		const clickEndTime = Date.now();
		const elapsedTime = clickEndTime - gClickStart.time;
		if ( DEBUG ) { console.log( `Click Elapsed: ${elapsedTime}` ); }
		handleClick( event );
		gClickTimeout = null;
	    }, DoubleClickDelayMs );
	}
    }
    
    function handleKeyDown( event ) {
	const targetArea = $(locationViewAreaSelector);
        const targetOffset = targetArea.offset();
        const targetWidth = targetArea.outerWidth();
        const targetHeight = targetArea.outerHeight();
	
        if (gLastMousePosition.x >= targetOffset.left && 
	    gLastMousePosition.x <= targetOffset.left + targetWidth &&
	    gLastMousePosition.y >= targetOffset.top &&
	    gLastMousePosition.y <= targetOffset.top + targetHeight) {

            displayEventInfo( 'Key Down', event );

	    if ( event.key == ActionScaleKey ) {
		actionRotateAbort();
		actionScaleStart();
		
	    } else if ( event.key == ActionRotateKey ) {
		actionScaleAbort();
		actionRotateStart();
		
	    } else if ( event.key == 'Escape' ) {
		actionScaleAbort();
		actionRotateAbort();
		gEditActionState = EditActionState.MOVE;
		$(baseSvgSelector).attr( EditActionStateAttrName, '');
		
	    } else {
		return;
	    }
	
	    event.stopPropagation();
	    event.preventDefault();   		
        }
    }
    
    function handleKeyUp( event ) {
        displayEventInfo( 'Key Up', event );
    }

    function handleClick( event ) {
        displayEventInfo( 'Click', event );
        displayElementInfo( 'Event Target', $(event.target) );

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length < 1 ) {
	    if ( DEBUG ) { console.log( 'NO TARGET'  ); }
	    gSelectedElement = null;
	    $('.draggable').removeClass('highlighted');
            AN.get( `/edit/details` );
	    return;
	}
        displayElementInfo( 'SVG Target Element', enclosingSvgGroup );

	const svgItemId = enclosingSvgGroup.attr('id');
	if ( ! svgItemId ) {
	    return;
	}

	gSelectedElement = enclosingSvgGroup;
	
	$('.draggable').removeClass('highlighted');
        $(enclosingSvgGroup).addClass('highlighted');
	
        AN.get( `/edit/details/${svgItemId}` );
    }
    
    function handleDoubleClick( event ) {
	// Currently no special double click handling defined. Revert to single click for now.
	handleClick( event );
    }
    
    function createDragData( event ) {	
        displayEventInfo( 'Create Drag', event );
        displayElementInfo( 'Event Target', $(event.target) );

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length < 1 ) {
	    return;
	}

	const dragElement = enclosingSvgGroup;
        displayElementInfo( 'Drag Element', dragElement );
	
	const baseSvgElement = $(baseSvgSelector);
	displayElementInfo( 'Base SVG', baseSvgElement );

        let transform = dragElement.attr('transform') || '';
        let { scale, translate, rotate } = getSvgTransformValues( transform );
        let cursorSvgPoint = toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	};

	gDragData = {
	    element: dragElement,
	    baseSvgElement: baseSvgElement,
	    cursorSvgOffset: cursorSvgOffset,
	    elementSvgCenterPoint: getSvgCenterPoint( dragElement, baseSvgElement ),
	    originalSvgScale: scale,
	    originalSvgRotate: rotate,
	    isDragging: false
	};
	
	if ( DEBUG ) {
	    console.log( `Drag Start:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ), 
    SVG Cursor Offset: ( ${gDragData.cursorSvgOffset.x}, ${gDragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${gDragData.elementSvgCenterPoint.x}, ${gDragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( gDragData == null ) {
	    return;
	}
        displayEventInfo( 'Update Drag', event );
        displayElementInfo( 'Drag Element', gDragData.element );

        let cursorSvgPoint = toSvgPoint( gDragData.baseSvgElement, event.clientX, event.clientY );

	let scale = gDragData.originalSvgScale;
	let rotate = gDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gDragData.cursorSvgOffset.y;

        let transform = gDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gDragData.element.attr('transform', newTransform);	    

	gDragData.elementSvgCenterPoint = getSvgCenterPoint( gDragData.element, gDragData.baseSvgElement );
	
	if ( DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${gDragData.elementSvgCenterPoint.x}, ${gDragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function endDrag( event ) {
        if ( gDragData == null ) {
	    return;
	}

	
        displayEventInfo( 'End Drag', event );
        displayElementInfo( 'Drag Element', gDragData.element );
	updateDrag( event );

	let svgItemId = gDragData.element.attr('id');
	data = {
	    svg_x: gDragData.elementSvgCenterPoint.x,
	    svg_y: gDragData.elementSvgCenterPoint.y,
	    svg_scale: gDragData.originalSvgScale.x,
	    svg_rotate: gDragData.originalSvgRotate.angle
	};
	AN.post( `/edit/svg/position/${svgItemId}`, data );

	gDragData = null;
    }
 
    function saveSvgPosition( element ) {

        let transform = element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const baseSvgElement = $(baseSvgSelector);
	const center = getSvgCenterPoint( element, baseSvgElement );

	let svgItemId = element.attr('id');
	data = {
	    svg_x: center.x,
	    svg_y: center.y,
	    svg_scale: scale.x,
	    svg_rotate: rotate.angle,
	};
	AN.post( `/edit/svg/position/${svgItemId}`, data );
    }

    function createEditActionData( actionState ) {
	if ( gSelectedElement ) {
            let transform = gSelectedElement.attr('transform');
            let { scale, translate, rotate } = getSvgTransformValues( transform );

	    gEditActionData = {
		element: gSelectedElement,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gEditActionState = actionState;
	    $(baseSvgSelector).attr( EditActionStateAttrName, actionState );
	}
    }

    function revertAction( element ) {
	if ( gEditActionData ) {
	    setSvgTransformAttr( gEditActionData.element,
				 gEditActionData.scaleStart,
				 gEditActionData.translateStart,
				 gEditActionData.rotateStart );
	    gEditActionData = null;
	}
    }
    
    function actionScaleStart() {
	createEditActionData( EditActionState.SCALE );	
    }

    function actionScaleUpdate( currentMousePosition ) {

	let center = getScreenCenterPoint( gEditActionData.element );

	let scaleFactor = getScaleFactor( center.x, center.y,
					  gLastMousePosition.x, gLastMousePosition.y,
					  currentMousePosition.x, currentMousePosition.y );
        let transform = gEditActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );

	const newScale = {
	    x: scale.x * scaleFactor,
	    y: scale.y * scaleFactor
	};
		
	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.y / newScale.y;

	if ( DEBUG ) {
	    console.log( `Scale Update:
    Transform:  ${transform}
    Scale = ${scale.x}, T = ${translate.x}, R = ${rotate.angle}` );
	}

	setSvgTransformAttr( gEditActionData.element, newScale, translate, rotate );

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
    
    function actionScaleApply() {
	if ( DEBUG ) { console.log( 'Scale Apply' ); }
	saveSvgPosition( gEditActionData.element );
    }

    function actionScaleAbort() {
	if ( gEditActionState != EditActionState.SCALE ) {
	    return;
	}
	revertAction();
    }

    function actionRotateStart() {
	createEditActionData( EditActionState.ROTATE );	
    }

    function actionRotateUpdate( currentMousePosition ) {
	if ( DEBUG ) { console.log( 'Rotate Update' ); }

	center = getScreenCenterPoint( gEditActionData.element );

	let deltaAngle = getRotationAngle( center.x, center.y,
					   gLastMousePosition.x, gLastMousePosition.y,
					   currentMousePosition.x, currentMousePosition.y );

        let transform = gEditActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = normalizeAngle( rotate.angle );
	setSvgTransformAttr( gEditActionData.element, scale, translate, rotate );
    }

    function getRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

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

    
    function actionRotateApply() {
	saveSvgPosition( gEditActionData.element );
    }
    
    function actionRotateAbort() {
	if ( gEditActionState != EditActionState.ROTATE ) {
	    return;
	}	
	revertAction();
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
		return toSvgPoint( svgElement, screenCenterX, screenCenterY );
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return { x: 0, y: 0 };
    }
    
    function toSvgPoint( svgElement, clientX, clientY) {
        let point = svgElement[0].createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( svgElement[0].getScreenCTM().inverse());
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

	if ( DEBUG ) {
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
    
    function getSvgViewBox( svgElement ) {
	let x = null;
	let y = null;
	let width = null;
	let height = null;

	if (svgElement.length < 1 ) {
	    return { x, y, width, height };
	}
        let viewBoxValue = svgElement.attr('viewBox');
        if ( ! viewBoxValue) {
	    return { x, y, width, height };
	}
	
	let viewBoxArray = viewBoxValue.split(' ').map(Number);
	x = viewBoxArray[0];
	y = viewBoxArray[1];
	width = viewBoxArray[2];
	height = viewBoxArray[3];

	return { x, y, width, height };
    }

    function normalizeAngle(angle) {
	return (angle % 360 + 360) % 360;
    }
    
    function displayEventInfo( label, event ) {
	if ( ! DEBUG ) { return; }
	if ( ! event ) {
            console.log( 'No element to display info for.' );
	    return;
	}
        console.log( `${label} Event: 
    Type: ${event.type}, 
    Key: ${event.key},
    Pos: ( ${event.clientX}, ${event.clientY} )` );
    }
    
    function displayElementInfo( label, element ) {
	if ( ! DEBUG ) { return; }
	if ( ! element ) {
            console.log( 'No element to display info for.' );
	    return;
	}
	const elementTag = element.prop('tagName');
	const elementId = element.attr('id') || 'No ID';
	const elementClasses = element.attr('class') || 'No Classes';

	let rectStr = 'No Bounding Rect';
	try {
            let rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		rectStr = `Dim: ${rect.width}px x ${rect.height}px,
    Pos: left=${rect.left}px, top=${rect.top}px`;
	    }
	} catch (e) {
	}
	
	let offsetStr = 'No Offset';
	const offset = element.offset();
	if ( offset ) {
	    offsetStr = `Offset: ( ${offset.left}px,  ${offset.top}px )`;
	}

	let svgStr = 'Not an SVG';
	if ( elementTag == 'svg' ) {
	    let { x, y, width, height } = getSvgViewBox( element );
	    if ( x != null ) {
		svgStr = `Viewbox: ( ${x}, ${y}, ${width}, ${height} )`;
	    } else {
		svgStr = 'No viewbox attribute';
	    }
	}
	
        console.log( `${label}: 
    Name: ${elementTag}, 
    Id: ${elementId},
    Classes: ${elementClasses},
    ${svgStr},
    ${offsetStr},
    ${rectStr}`) ;

    }
    
})();
