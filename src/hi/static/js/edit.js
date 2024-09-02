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

    const ActionState = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };    
    const ActionStateAttrName = 'action-state';
    const ActionMoveKey = 'm';
    const ActionScaleKey = 's';
    const ActionRotateKey = 'r';

    const DoubleClickDelayMs = 300;
    const DragThreshold = 3;
    
    let gActionState = ActionState.MOVE;
    let selectedElement = null;

    let clickStart = null;
    let clickTimeout = null;
    let lastMousePosition = { x: 0, y: 0 };

    let dragData = null;
    let actionData = null;
    
    $(document).ready(function() {
	$(document).on('mousedown', locationViewAreaSelector, function(event) {

	    // Need to track time to differentiate drag/scale/rotate actions from regular clicks.
	    clickStart = {
		x: event.clientX,
		y: event.clientY,
		time: Date.now()
	    };

	    if ( gActionState == ActionState.MOVE ) {
		createDragData( event );
		return;
	    } 
	    if ( actionData ) {
		if ( gActionState == ActionState.SCALE ) {
		    actionData.isScaling = true;
		} else if ( gActionState == ActionState.ROTATE ) {
		    actionData.isRotating = true;
		}
	    }
	});
	$(document).on('mousemove', locationViewAreaSelector, function(event) {
	    const currentMousePosition = {
		x: event.clientX,
		y: event.clientY
	    };
	    
	    if ( dragData ) {
		const distanceX = Math.abs( currentMousePosition.x - clickStart.x );
		const distanceY = Math.abs( currentMousePosition.y - clickStart.y );
	    
		if ( dragData.isDragging || ( distanceX > DragThreshold ) || ( distanceY > DragThreshold )) {
		    dragData.isDragging = true;
		    $(baseSvgSelector).attr( ActionStateAttrName, ActionState.MOVE);
		    updateDrag(event);
		}
	    }
	    else if ( actionData ) {
		if ( actionData.isScaling ) {
		    actionScaleUpdate( currentMousePosition );
		} else if ( actionData.isRotating ) {
		    actionRotateUpdate( currentMousePosition );
		}
	    }

	    lastMousePosition = currentMousePosition;
	});
	$(document).on('mouseup', locationViewAreaSelector, function(event) {
	    if ( dragData ) {
		if ( dragData.isDragging ) {
		    endDrag( event );
		    return;
		}
		$(baseSvgSelector).attr( ActionStateAttrName, '' );
		dragData = null;
	    }


	    else if ( actionData ) {
		if ( gActionState == ActionState.SCALE ) {
		    actionData.isScaling = false;
		    actionScaleApply();
		} else if ( gActionState == ActionState.ROTATE ) {
		    actionData.isRotating = false;
		    actionRotateApply();
		}
		actionData = null;
	    }
	    
	    if ( clickTimeout ) {
		const clickEndTime = Date.now();
		const elapsedTime = clickEndTime - clickStart.time;
		console.log( `Click Elapsed: ${elapsedTime}` );
		clearTimeout( clickTimeout );
		clickTimeout = null;
		handleDoubleClick( event );
	    } else {
		clickTimeout = setTimeout(() => {
		    const clickEndTime = Date.now();
		    const elapsedTime = clickEndTime - clickStart.time;
		    console.log( `Click Elapsed: ${elapsedTime}` );
		    handleClick( event );
		    clickTimeout = null;
		}, DoubleClickDelayMs );
	    }
	});
	$(document).on('keydown', function(event) {
	    const targetArea = $(locationViewAreaSelector);
            const targetOffset = targetArea.offset();
            const targetWidth = targetArea.outerWidth();
            const targetHeight = targetArea.outerHeight();
	    
            if (lastMousePosition.x >= targetOffset.left && 
		lastMousePosition.x <= targetOffset.left + targetWidth &&
		lastMousePosition.y >= targetOffset.top &&
		lastMousePosition.y <= targetOffset.top + targetHeight) {
		handleKeyDown(event);
            }	
	});
	$(document).on('keyup', function(event) {
	    handleKeyUp( event );
	});
    });

    function handleClick( event ) {
        displayEventInfo( 'Click', event );
        displayElementInfo( 'Event Target', $(event.target) );

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length < 1 ) {
	    return;
	}
        displayElementInfo( 'SVG Target Element', enclosingSvgGroup );

	const svgItemId = enclosingSvgGroup.attr('id');
	if ( ! svgItemId ) {
	    return;
	}

	selectedElement = enclosingSvgGroup;
	
	$('.draggable').removeClass('highlighted');
        $(enclosingSvgGroup).addClass('highlighted');
	
        AN.get( `/edit/details/${svgItemId}` );
    }
    
    function handleDoubleClick( event ) {
        displayEventInfo( 'Double Click', event );
        displayElementInfo( 'Event Target', $(event.target) );

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length < 1 ) {
	    return;
	}
        displayElementInfo( 'SVG Target Element', enclosingSvgGroup );
	
    }
    
    function handleKeyDown( event ) {
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
	    gActionState = ActionState.MOVE;
	    $(baseSvgSelector).attr( ActionStateAttrName, '');
	    
	} else {
	    return;
	}
	
	event.stopPropagation();
	event.preventDefault();   		
    }

    function handleKeyUp( event ) {
        displayEventInfo( 'Key Up', event );
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
        let { scale, translate, rotate } = getTransformValues( transform );
        let cursorSvgPoint = toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	const cursorSvgOffset = {
	    x : (cursorSvgPoint.x / scale.x) - translate.x,
	    y : (cursorSvgPoint.y / scale.y) - translate.y
	}

	dragData = {
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
    SVG Cursor Offset: ( ${dragData.cursorSvgOffset.x}, ${dragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${dragData.elementSvgCenterPoint.x}, ${dragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( dragData == null ) {
	    return;
	}
        displayEventInfo( 'Update Drag', event );
        displayElementInfo( 'Drag Element', dragData.element );

        let cursorSvgPoint = toSvgPoint( dragData.baseSvgElement, event.clientX, event.clientY );

	let scale = dragData.originalSvgScale;
	let rotate = dragData.originalSvgRotate
	
        let newX = (cursorSvgPoint.x / scale.x) - dragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - dragData.cursorSvgOffset.y;

        let transform = dragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        dragData.element.attr('transform', newTransform);	    

	dragData.elementSvgCenterPoint = getSvgCenterPoint( dragData.element, dragData.baseSvgElement );
	
	if ( DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${dragData.elementSvgCenterPoint.x}, ${dragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function endDrag( event ) {
        if ( dragData == null ) {
	    return;
	}

	
        displayEventInfo( 'End Drag', event );
        displayElementInfo( 'Drag Element', dragData.element );
	updateDrag( event );

	let svgItemId = dragData.element.attr('id');
	data = {
	    svg_x: dragData.elementSvgCenterPoint.x,
	    svg_y: dragData.elementSvgCenterPoint.y,
	    svg_scale: dragData.originalSvgScale.x,
	    svg_rotate: dragData.originalSvgRotate.angle
	};
	AN.post( `/edit/svg/position/${svgItemId}`, data );

	dragData = null;
    }
 
    function getTransformValues(transform) {
	let scale = { x: 1, y: 1 }, rotate = { angle: 0, cx: 0, cy: 0 }, translate = { x: 0, y: 0 };

	let scaleMatch = transform.match(/scale\(([^)]+)\)/);
	if (scaleMatch) {
	    let scaleValues = scaleMatch[1].trim().split(/[ ,]+/).map(parseFloat);
	    scale.x = scaleValues[0]
	    if ( scaleValues.length == 1 ) {
		scale.y = scale.x;
	    } else {
		scale.y = scaleValues[1]
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
    
    function saveSvgPosition( element ) {

        let transform = element.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );

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

    function createActionData( actionState ) {
	if ( selectedElement ) {
            let transform = selectedElement.attr('transform');
            let { scale, translate, rotate } = getTransformValues( transform );
	    
	    actionData = {
		element: selectedElement,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gActionState = actionState;
	    $(baseSvgSelector).attr( ActionStateAttrName, actionState );
	}
    }

    function revertAction( element ) {
	if ( actionData ) {
	    setSvgTransformAttr( actionData.element,
				 actionData.scaleStart,
				 actionData.translateStart,
				 actionData.rotateStart );
	    actionData = null;
	}
    }
    
    function actionScaleStart() {
	createActionData( ActionState.SCALE );	
    }

    function actionRotateStart() {
	createActionData( ActionState.ROTATE );	
    }

    function actionScaleUpdate( currentMousePosition ) {
	console.log( 'Scale Update' );
	const deltaX = currentMousePosition.x - lastMousePosition.x;
	const deltaY = currentMousePosition.y - lastMousePosition.y;
	if (( deltaX <= DragThreshold ) && ( deltaY <= DragThreshold )) {
	    return;
	}
        let transform = actionData.element.attr('transform');
	console.log( `T = ${transform}` );
        let { scale, translate, rotate } = getTransformValues( transform );
	console.log( `SCALE = ${scale}, T = ${translate}, R = ${rotate}` );
	const newScale = {
	    x: scale.x + 0.01 * deltaX,
	    y: scale.x + 0.01 * deltaX
	};
	
	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.x / newScale.x;

	setSvgTransformAttr( actionData.element, newScale, translate, rotate );
    }
    
    function actionRotateUpdate( currentMousePosition ) {
	const deltaX = currentMousePosition.x - lastMousePosition.x;
	const deltaY = currentMousePosition.y - lastMousePosition.y;
	if (( deltaX <= DragThreshold ) && ( deltaY <= DragThreshold )) {
	    return;
	}
	const rotateDelta = {
	    angle: deltaX
	};
        let transform = actionData.element.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );
	rotate.angle += deltaX;
	setSvgTransformAttr( actionData.element, scale, translate, rotate );
    }
    
    function actionScaleApply() {
	console.log( 'Scale Apply' );
	saveSvgPosition( actionData.element );
    }

    function actionRotateApply() {
	saveSvgPosition( actionData.element );
    }
    
    function actionScaleAbort() {
	if ( gActionState != ActionState.SCALE ) {
	    return;
	}
	revertAction();
    }

    function actionRotateAbort() {
	if ( gActionState != ActionState.ROTATE ) {
	    return;
	}	
	revertAction();
    }

    function getSvgCenterPoint( element, svgElement ) {

	try {
            rect = element[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return toSvgPoint( svgElement, screenCenterX, screenCenterY );
	    }
	} catch (e) {
	    console.debug( `Problem getting bounding box: ${e}` );
	}
	return { x: 0, y: 0 }
    }
    
    function toSvgPoint( svgElement, clientX, clientY) {
        let point = svgElement[0].createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( svgElement[0].getScreenCTM().inverse());
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

	return { x, y, width, height }
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
            rect = element[0].getBoundingClientRect();
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
