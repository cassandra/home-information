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

    const SvgActionStateType = {
	MOVE: 'move',
	SCALE: 'scale',
	ROTATE: 'rotate'
    };    
    const SvgActionStateAttrName = 'action-state';
    const ActionMoveKey = 'm';
    const ActionScaleKey = 's';
    const ActionRotateKey = 'r';

    const DoubleClickDelayMs = 300;
    const CursorMovementThreshold = 3;
    
    let gSvgActionState = SvgActionStateType.MOVE;
    let gSelectedElement = null;

    let gClickStart = null;
    let gClickTimeout = null;
    let gLastMousePosition = { x: 0, y: 0 };

    let gSvgDragData = null;
    let gSvgActionData = null;
    let gDraggedElement = null;
    
    $(document).ready(function() {

	$('.draggable').on('dragstart', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragStart( event );
	});
	$('.draggable').on('dragend', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnd( event );
	});
	$('.draggable').on('dragover', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragOver( event );
	});
	$('.draggable').on('dragenter', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragEnter( event );
	});
	$('.draggable').on('dragleave', function(event) {
	    if ( gHiViewMode != 'edit' ) { return; }
	    handleDragLeave( event );
	});

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

    function handleDragStart( event ) {
	if ( DEBUG ) { console.log('event.currentTarget:', event.currentTarget); }

        gDraggedElement = event.currentTarget;
	
        // Hide the dragged element during the drag operation for better visuals
        setTimeout(() => {
            $(gDraggedElement).hide();
	    console.log('Hidden class added');
        }, 0);
    }
    
    function handleDragEnd( event ) {
	if ( DEBUG ) { console.log('Drag end:'); }
        $(gDraggedElement).show();
        gDraggedElement = null;
	$('.draggable').removeClass('drag-over');
	$('.draggable').css('transform', '');
	
        var htmlIdList = [];
	var parentContainer = $(event.currentTarget).closest('.draggable-container');
        parentContainer.find('.draggable').each(function() {
            htmlIdList.push($(this).attr('data-id'));
        });
	
	if ( DEBUG ) { console.log(`Drag end ids: ${htmlIdList}`); }

	data = {
	    html_id_list: JSON.stringify( htmlIdList ),
	};
	AN.post( `/edit/reorder-items`, data );
    }
    
    function handleDragOver( event ) {
	if ( DEBUG ) { console.log('Drag over:'); }
        event.preventDefault();
	
        // Ensure the dragged element is in the same parent container
        if (( gDraggedElement !== event.currentTarget )
	    && ( $(event.currentTarget).parent()[0] === $(gDraggedElement).parent()[0] )) {
            const bounding = event.currentTarget.getBoundingClientRect();
            const offset = bounding.y + bounding.height / 2;

            // Insert dragged element before or after depending on mouse position
            if (event.clientY - offset > 0) {
                $(event.currentTarget).css('transform', 'translateX(50px)');
               $(event.currentTarget).after(gDraggedElement);
            } else {
                $(event.currentTarget).css('transform', 'translateX(-50px)');
               $(event.currentTarget).before(gDraggedElement);
            }
        }	
    }
    
    function handleDragEnter( event ) {
	if ( DEBUG ) { console.log('Drag enter:'); }
	// Only allow visual feedback if in the same parent container
        if ( $(event.currentTarget).parent()[0] === $(gDraggedElement).parent()[0] ) {
            $(event.currentTarget).addClass('drag-over');
        }
    }
    
    function handleDragLeave( event ) {
	if ( DEBUG ) { console.log('Drag leave:'); }
	$(event.currentTarget).removeClass('drag-over');
	$(event.currentTarget).css('transform', '');  
    }
    
    function handleMouseDown( event ) {
	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	    time: Date.now()
	};
	
	if ( gSvgActionState == SvgActionStateType.MOVE ) {
	    createDragData( event );
	    return;
	} 
	if ( gSvgActionData ) {
	    if ( gSvgActionState == SvgActionStateType.SCALE ) {
		gSvgActionData.isScaling = true;
	    } else if ( gSvgActionState == SvgActionStateType.ROTATE ) {
		gSvgActionData.isRotating = true;
	    }
	}
    }
    
    function handleMouseMove( event ) {
	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	
	if ( gSvgDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gSvgDragData.isDragging || ( distanceX > CursorMovementThreshold ) || ( distanceY > CursorMovementThreshold )) {
		gSvgDragData.isDragging = true;
		$(baseSvgSelector).attr( SvgActionStateAttrName, SvgActionStateType.MOVE);
		updateDrag(event);
	    }
	}
	else if ( gSvgActionData ) {
	    if ( gSvgActionData.isScaling ) {
		actionScaleUpdate( currentMousePosition );
	    } else if ( gSvgActionData.isRotating ) {
		actionRotateUpdate( currentMousePosition );
	    }
	}
	
	gLastMousePosition = currentMousePosition;
    }
    
    function handleMouseUp( event ) {
	if ( gSvgDragData ) {
	    if ( gSvgDragData.isDragging ) {
		endDrag( event );
		$(baseSvgSelector).attr( SvgActionStateAttrName, '');
		return;
	    }
	    $(baseSvgSelector).attr( SvgActionStateAttrName, '' );
	    gSvgDragData = null;
	}
	
	else if ( gSvgActionData ) {
	    if ( gSvgActionState == SvgActionStateType.SCALE ) {
		gSvgActionData.isScaling = false;
		actionScaleApply();
	    } else if ( gSvgActionState == SvgActionStateType.ROTATE ) {
		gSvgActionData.isRotating = false;
		actionRotateApply();
	    }
	    gSvgActionState = SvgActionStateType.MOVE;
	    $(baseSvgSelector).attr( SvgActionStateAttrName, '');
	    gSvgActionData = null;
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
		gSvgActionState = SvgActionStateType.MOVE;
		$(baseSvgSelector).attr( SvgActionStateAttrName, '');
		
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

	gSvgDragData = {
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
    SVG Cursor Offset: ( ${gSvgDragData.cursorSvgOffset.x}, ${gSvgDragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${gSvgDragData.elementSvgCenterPoint.x}, ${gSvgDragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( gSvgDragData == null ) {
	    return;
	}
        displayEventInfo( 'Update Drag', event );
        displayElementInfo( 'Drag Element', gSvgDragData.element );

        let cursorSvgPoint = toSvgPoint( gSvgDragData.baseSvgElement, event.clientX, event.clientY );

	let scale = gSvgDragData.originalSvgScale;
	let rotate = gSvgDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gSvgDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gSvgDragData.cursorSvgOffset.y;

        let transform = gSvgDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gSvgDragData.element.attr('transform', newTransform);	    

	gSvgDragData.elementSvgCenterPoint = getSvgCenterPoint( gSvgDragData.element, gSvgDragData.baseSvgElement );
	
	if ( DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${cursorSvgPoint.x}, ${cursorSvgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${gSvgDragData.elementSvgCenterPoint.x}, ${gSvgDragData.elementSvgCenterPoint.y} )`); 
	}
    }
    
    function endDrag( event ) {
        if ( gSvgDragData == null ) {
	    return;
	}

	
        displayEventInfo( 'End Drag', event );
        displayElementInfo( 'Drag Element', gSvgDragData.element );
	updateDrag( event );

	let svgItemId = gSvgDragData.element.attr('id');
	data = {
	    svg_x: gSvgDragData.elementSvgCenterPoint.x,
	    svg_y: gSvgDragData.elementSvgCenterPoint.y,
	    svg_scale: gSvgDragData.originalSvgScale.x,
	    svg_rotate: gSvgDragData.originalSvgRotate.angle
	};
	AN.post( `/edit/svg/position/${svgItemId}`, data );

	gSvgDragData = null;
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

	    gSvgActionData = {
		element: gSelectedElement,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gSvgActionState = actionState;
	    $(baseSvgSelector).attr( SvgActionStateAttrName, actionState );
	}
    }

    function revertAction( element ) {
	if ( gSvgActionData ) {
	    setSvgTransformAttr( gSvgActionData.element,
				 gSvgActionData.scaleStart,
				 gSvgActionData.translateStart,
				 gSvgActionData.rotateStart );
	    gSvgActionData = null;
	}
    }
    
    function actionScaleStart() {
	createEditActionData( SvgActionStateType.SCALE );	
    }

    function actionScaleUpdate( currentMousePosition ) {

	let center = getScreenCenterPoint( gSvgActionData.element );

	let scaleFactor = getScaleFactor( center.x, center.y,
					  gLastMousePosition.x, gLastMousePosition.y,
					  currentMousePosition.x, currentMousePosition.y );
        let transform = gSvgActionData.element.attr('transform');
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

	setSvgTransformAttr( gSvgActionData.element, newScale, translate, rotate );

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
	saveSvgPosition( gSvgActionData.element );
    }

    function actionScaleAbort() {
	if ( gSvgActionState != SvgActionStateType.SCALE ) {
	    return;
	}
	revertAction();
    }

    function actionRotateStart() {
	createEditActionData( SvgActionStateType.ROTATE );	
    }

    function actionRotateUpdate( currentMousePosition ) {
	if ( DEBUG ) { console.log( 'Rotate Update' ); }

	center = getScreenCenterPoint( gSvgActionData.element );

	let deltaAngle = getRotationAngle( center.x, center.y,
					   gLastMousePosition.x, gLastMousePosition.y,
					   currentMousePosition.x, currentMousePosition.y );

        let transform = gSvgActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = normalizeAngle( rotate.angle );
	setSvgTransformAttr( gSvgActionData.element, scale, translate, rotate );
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
	saveSvgPosition( gSvgActionData.element );
    }
    
    function actionRotateAbort() {
	if ( gSvgActionState != SvgActionStateType.ROTATE ) {
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
