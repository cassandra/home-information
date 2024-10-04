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
    
    let gSvgIconActionState = SvgActionStateType.MOVE;
    let gSelectedIconSvgGroup = null;
    let gSvgIconDragData = null;
    let gSvgIconActionData = null;

    let gSelectedPathSvgGroup = null;
    let gSvgPathEditData = null;
    
    let gClickStart = null;
    let gClickTimeout = null;
    let gLastMousePosition = { x: 0, y: 0 };


    // For re-ordering items (buttons, lists, etc)
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
	if ( DEBUG ) {
            displayEventInfo( 'Mouse down event: ', event );
            displayElementInfo( 'Event target: ', $(event.target) );
	}

	// Path editing does its own special mouse event handling on a per-element basis..
	if ( gSvgPathEditData ) {
	    return;
	}
	
	// Need to track start time to differentiate drag/scale/rotate actions from regular clicks.
	gClickStart = {
	    x: event.clientX,
	    y: event.clientY,
	    time: Date.now()
	};
	
	if ( gSvgIconActionState == SvgActionStateType.MOVE ) {

	    const enclosingSvgGroup = $(event.target).closest('g');
	    if ( enclosingSvgGroup.length < 1 ) {
		return;
	    }
	    const svgDataType = $(enclosingSvgGroup).attr('data-type');
	    if ( svgDataType == 'svg-icon' ) {
		createIconDragData( event, enclosingSvgGroup );
	    }
	    return;
	} 
	if ( gSvgIconActionData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionData.isScaling = true;
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionData.isRotating = true;
	    }
	}
    }
    
    function handleMouseMove( event ) {

	const currentMousePosition = {
	    x: event.clientX,
	    y: event.clientY
	};
	
	if ( gSvgIconDragData ) {
	    const distanceX = Math.abs( currentMousePosition.x - gClickStart.x );
	    const distanceY = Math.abs( currentMousePosition.y - gClickStart.y );
	    
	    if ( gSvgIconDragData.isDragging || ( distanceX > CursorMovementThreshold ) || ( distanceY > CursorMovementThreshold )) {
		gSvgIconDragData.isDragging = true;
		$(baseSvgSelector).attr( SvgActionStateAttrName, SvgActionStateType.MOVE);
		updateDrag(event);
	    }
	}
	else if ( gSvgIconActionData ) {
	    if ( gSvgIconActionData.isScaling ) {
		iconActionScaleUpdate( currentMousePosition );
	    } else if ( gSvgIconActionData.isRotating ) {
		iconActionRotateUpdate( currentMousePosition );
	    }
	}
	
	gLastMousePosition = currentMousePosition;
    }
    
    function handleMouseUp( event ) {
	if ( gSvgIconDragData ) {
	    if ( gSvgIconDragData.isDragging ) {
		endDrag( event );
		$(baseSvgSelector).attr( SvgActionStateAttrName, '');
		return;
	    }
	    $(baseSvgSelector).attr( SvgActionStateAttrName, '' );
	    gSvgIconDragData = null;
	}
	
	else if ( gSvgIconActionData ) {
	    if ( gSvgIconActionState == SvgActionStateType.SCALE ) {
		gSvgIconActionData.isScaling = false;
		iconActionScaleApply();
	    } else if ( gSvgIconActionState == SvgActionStateType.ROTATE ) {
		gSvgIconActionData.isRotating = false;
		iconActionRotateApply();
	    }
	    gSvgIconActionState = SvgActionStateType.MOVE;
	    $(baseSvgSelector).attr( SvgActionStateAttrName, '');
	    gSvgIconActionData = null;
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
	if ( $(event.target).is('input[type="text"], textarea') ) {
            return;
	}
	else if ( gSelectedIconSvgGroup ) {
	    handleSvgIconSelectedKeyDown( event );
	}
	else if ( gSvgPathEditData ) {
	    handleSvgPathEditKeyDown( event );
	}
    }

    function handleSvgIconSelectedKeyDown( event ) {
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
		iconActionRotateAbort();
		iconActionScaleStart();
		
	    } else if ( event.key == ActionRotateKey ) {
		iconActionScaleAbort();
		iconActionRotateStart();
		
	    } else if ( event.key == 'Escape' ) {
		iconActionScaleAbort();
		iconActionRotateAbort();
		gSvgIconActionState = SvgActionStateType.MOVE;
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
	if ( enclosingSvgGroup.length > 0 ) {
            displayElementInfo( 'SVG Target Element', enclosingSvgGroup );
	    const selectable = $(enclosingSvgGroup).hasClass('selectable');
	    const svgItemId = enclosingSvgGroup.attr('id');
	    if ( selectable && svgItemId ) {
		handleSvgItemClick( event, enclosingSvgGroup );
		return;
	    }
	}

	if ( gSvgPathEditData ) {
	    handleSvgPathEditClick( event );
	} else {
	    if ( DEBUG ) { console.log( 'No SVG group for click target'  ); }
	    clearSelectedAll();
            AN.get( `/edit/details` );
	    return;
	}
    }

    function handleSvgItemClick( event, enclosingSvgGroup ) {
	const svgItemId = $(enclosingSvgGroup).attr('id');
	const svgDataType = $(enclosingSvgGroup).attr('data-type');
	if ( svgDataType == 'svg-icon' ) {
	    clearSelectedAll();
	    gSelectedIconSvgGroup = enclosingSvgGroup;
            $(enclosingSvgGroup).addClass('highlighted');
            AN.get( `/edit/details/${svgItemId}` );
	    
	} else if ( svgDataType == 'svg-path' ) {
	    clearSelectedAll();
	    gSelectedPathSvgGroup = enclosingSvgGroup;
	    expandSvgPath( enclosingSvgGroup );
            AN.get( `/edit/details/${svgItemId}` );
	    
	} else {
	    if ( DEBUG ) { console.log( `Unrecognized SVG group "${svgDataType}" for click target`  ); }
	}
	
    }
    
    function handleDoubleClick( event ) {
	// Currently no special double click handling defined. Revert to single click for now.
	handleClick( event );
    }
    
    function clearSelectedAll() {
	clearSelectedSvgIcon();
	clearSelectedSvgPath();
	$('.selectable').removeClass('highlighted');
    }

    function clearSelectedSvgIcon() {
	if ( gSelectedIconSvgGroup ) {
	    $(gSelectedIconSvgGroup).removeClass('highlighted');
	    gSelectedIconSvgGroup = null;
	}
    }

    function clearSelectedSvgPath() {
	if ( gSelectedPathSvgGroup ) {
	    collapseSvgPath( gSelectedPathSvgGroup );
	    gSelectedPathSvgGroup = null;
	}
    }

    function createIconDragData( event, enclosingSvgGroup ) {	

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

	gSvgIconDragData = {
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
    SVG Cursor Offset: ( ${gSvgIconDragData.cursorSvgOffset.x}, ${gSvgIconDragData.cursorSvgOffset.y} ),
    SVG Center Point: ( ${gSvgIconDragData.elementSvgCenterPoint.x}, ${gSvgIconDragData.elementSvgCenterPoint.y} )`); 
	}
	
    }
    
    function updateDrag( event ) {
        if ( gSvgIconDragData == null ) {
	    return;
	}
        displayEventInfo( 'Update Drag', event );
        displayElementInfo( 'Drag Element', gSvgIconDragData.element );

        let cursorSvgPoint = toSvgPoint( gSvgIconDragData.baseSvgElement, event.clientX, event.clientY );

	let scale = gSvgIconDragData.originalSvgScale;
	let rotate = gSvgIconDragData.originalSvgRotate;
	
        let newX = (cursorSvgPoint.x / scale.x) - gSvgIconDragData.cursorSvgOffset.x;
        let newY = (cursorSvgPoint.y / scale.y) - gSvgIconDragData.cursorSvgOffset.y;

        let transform = gSvgIconDragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        gSvgIconDragData.element.attr('transform', newTransform);	    

	gSvgIconDragData.elementSvgCenterPoint = getSvgCenterPoint( gSvgIconDragData.element, gSvgIconDragData.baseSvgElement );
	
	if ( DEBUG ) {
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

	
        displayEventInfo( 'End Drag', event );
        displayElementInfo( 'Drag Element', gSvgIconDragData.element );
	updateDrag( event );

	let svgItemId = gSvgIconDragData.element.attr('id');
	data = {
	    svg_x: gSvgIconDragData.elementSvgCenterPoint.x,
	    svg_y: gSvgIconDragData.elementSvgCenterPoint.y,
	    svg_scale: gSvgIconDragData.originalSvgScale.x,
	    svg_rotate: gSvgIconDragData.originalSvgRotate.angle
	};
	AN.post( `/edit/svg/position/${svgItemId}`, data );

	gSvgIconDragData = null;
    }
 
    function saveIconSvgPosition( element ) {

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

    function createIconEditActionData( actionState ) {
	if ( gSelectedIconSvgGroup ) {
            let transform = gSelectedIconSvgGroup.attr('transform');
            let { scale, translate, rotate } = getSvgTransformValues( transform );

	    gSvgIconActionData = {
		element: gSelectedIconSvgGroup,
		scaleStart: scale,
		translateStart: translate,
		rotateStart: rotate,
		isScaling: false,
		isRotating: false
	    };

	    gSvgIconActionState = actionState;
	    $(baseSvgSelector).attr( SvgActionStateAttrName, actionState );
	}
    }

    function revertIconAction( element ) {
	if ( gSvgIconActionData ) {
	    setSvgTransformAttr( gSvgIconActionData.element,
				 gSvgIconActionData.scaleStart,
				 gSvgIconActionData.translateStart,
				 gSvgIconActionData.rotateStart );
	    gSvgIconActionData = null;
	}
    }
    
    function iconActionScaleStart() {
	createIconEditActionData( SvgActionStateType.SCALE );	
    }

    function iconActionScaleUpdate( currentMousePosition ) {

	let center = getScreenCenterPoint( gSvgIconActionData.element );

	let scaleFactor = getScaleFactor( center.x, center.y,
					  gLastMousePosition.x, gLastMousePosition.y,
					  currentMousePosition.x, currentMousePosition.y );
        let transform = gSvgIconActionData.element.attr('transform');
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

	setSvgTransformAttr( gSvgIconActionData.element, newScale, translate, rotate );

    }

    function iconActionScaleApply() {
	if ( DEBUG ) { console.log( 'Scale Apply' ); }
	saveIconSvgPosition( gSvgIconActionData.element );
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
	if ( DEBUG ) { console.log( 'Rotate Update' ); }

	center = getScreenCenterPoint( gSvgIconActionData.element );

	let deltaAngle = getIconRotationAngle( center.x, center.y,
					   gLastMousePosition.x, gLastMousePosition.y,
					   currentMousePosition.x, currentMousePosition.y );

        let transform = gSvgIconActionData.element.attr('transform');
        let { scale, translate, rotate } = getSvgTransformValues( transform );
	rotate.angle += deltaAngle;
	rotate.angle = normalizeAngle( rotate.angle );
	setSvgTransformAttr( gSvgIconActionData.element, scale, translate, rotate );
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
	saveIconSvgPosition( gSvgIconActionData.element );
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


    /* ================================================================================
      SVG PATH EDITING
      
      - Two types of paths: closed (with ending 'Z') and open.
      - The type is determined by the initial path and not editable.
      - An open path must have at least two control points.
      - A closed path must have at least 3 control points.
      - The behavior of adding to the path depends on its type.
      - An open path gets extended when adding.
      - A closed path has its lines subdivided when adding.
      - Adding is relative to the last selected item.
      - You can select a line or a control point.
    */    

    function handleSvgPathEditClick( event ) {
	if ( DEBUG ) { console.log( 'Path Edit Click' ); }

	const isProxyElement = $(event.target).hasClass('proxy');
	if ( isProxyElement ) {
	    setSelectedProxyElement( event.target );
	}
	else {
	    extendProxyPath( event );
	}
    }

    function handleSvgPathEditKeyDown( event ) {

	/*
	  DEL/x = if control, delete and connecting lines (must always have two control points
	  'a/i' = add control, extend line from end of selected. If closed, subdivide line connected to current
	*/
	
	console.log( 'PATH EDIT KEYDOWN' );
    }

    function setSelectedProxyElement( proxyElement ) {
	if ( ! gSvgPathEditData ) {
	    return;
	}
	$(gSvgPathEditData.proxyPathContainer).find('.proxy').removeClass('highlighted');
	$(proxyElement).addClass('highlighted');
	gSvgPathEditData.selectedProxyElement = proxyElement;
    }
    
    function expandSvgPath( pathSvgGroup ) {
	if ( DEBUG ) { console.log( 'Expand SVG Path', pathSvgGroup ); }

	pathSvgGroup.hide();

	const baseSvgElement = $(baseSvgSelector)[0];
	const proxyPathContainer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
	proxyPathContainer.setAttribute('id', 'hi-proxy-path-container');
	baseSvgElement.appendChild( proxyPathContainer );
	
	gSvgPathEditData = {
	    proxyPathContainer: proxyPathContainer,
	    selectedProxyElement: null
	};
	
	let svgPathElement = $(pathSvgGroup).find('path');
	const pathData = svgPathElement.attr('d');
	const segments = pathData.match(/[ML][^MLZ]+|Z/g);
	if ( DEBUG ) { console.log('Path segments', segments ); }

	/* Algorithm Description:

	   - We first create all the control points in the first loop.
	   - This builds the data structures to handle possibly having multiple line segments.
	   - We then iterate though all the line segments.
	   - We'll create all the lines and handlers for "interior" lines/points.
	   - Finally, we deal with the special cases of the first and last control points.
	   - First and last control points have only one line unless it is a closed path.
	   - If it is a closed path, we also need to add an extra line to close the figure.
	   - We organize all the proxy item into SVG groups:
	   - A SVG group excloses all with one child SVG group for each line segment (called a proxyPath)
	*/

	// Create all control points.
	let currentProxyPathGroup = null;
	for ( let i = 0; i < segments.length; i++ ) {
	    
            let command = segments[i].charAt(0);  // M or L or Z
            let coords = segments[i].substring(1).trim().split(/[\s,]+/).map(Number);

            if (command === 'M') {
		currentProxyPathGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
		currentProxyPathGroup.setAttribute('id', `hi-proxy-path-${i}` );
		currentProxyPathGroup.setAttribute('class', 'hi-proxy-path' );
		currentProxyPathGroup.setAttribute('hi-proxy-path-type', 'open' );
		proxyPathContainer.appendChild( currentProxyPathGroup );
		createProxyPathControlPoint( currentProxyPathGroup, coords[0], coords[1] );

            } else if (command === 'L' && currentProxyPathGroup ) {
		createProxyPathControlPoint( currentProxyPathGroup, coords[0], coords[1] );

            } else if (command === 'Z' && currentProxyPathGroup ) {
		currentProxyPathGroup.setAttribute('hi-proxy-path-type', 'closed' );
		currentProxyPathGroup = null;
            }
	}

	// Paths can have multiple segments
	$(proxyPathContainer).find( 'g.hi-proxy-path' ).each(function( index, proxyPathGroup ) {

	    if ( DEBUG ) { console.log( 'Proxy path group: ', proxyPathGroup ); }
	    
	    // Create interior lines and control point handlers with bookkeeping for first/last edge cases.
	    let previousControlPoint = null;
	    let firstLine = null;
	    let previousLine = null;

	    let controlPoints = $(proxyPathGroup).find( 'circle.proxy-point' );
	    
	    $(controlPoints).each(function( index, currentControlPoint ) {

		if ( previousControlPoint ) {
		    const x1 = parseFloat(previousControlPoint.getAttribute('cx'));
		    const y1 = parseFloat(previousControlPoint.getAttribute('cy'));
		    const x2 = parseFloat(currentControlPoint.getAttribute('cx'));
		    const y2 = parseFloat(currentControlPoint.getAttribute('cy'));
		    let currentLine = createProxyPathLine( proxyPathGroup, x1, y1, x2, y2 );
		    
		    if ( previousLine ) {
			addControlPointEventHandler( previousControlPoint, previousLine, currentLine );
		    }
		    if ( ! firstLine ) {
			firstLine = currentLine;
		    }
		    previousLine = currentLine;
		}

		previousControlPoint = currentControlPoint;
	    });

	    // Degerate cases of zero or one point and no lines.
	    if ( controlPoints.length < 2 ) {
		addControlPointEventHandler( previousControlPoint, null, null );
		return;
	    }
	    
	    // Edge cases for first and last points.
	    let firstControlPoint = controlPoints[0];
	    let lastControlPoint = controlPoints[controlPoints.length -1];
	    
	    if ( $(proxyPathGroup).attr('hi-proxy-path-type') == 'open' ) {
		addControlPointEventHandler( firstControlPoint, null, firstLine );
		addControlPointEventHandler( lastControlPoint, previousLine, null );
	    } else {
		const x1 = parseFloat(lastControlPoint.getAttribute('cx'));
		const y1 = parseFloat(lastControlPoint.getAttribute('cy'));
		const x2 = parseFloat(firstControlPoint.getAttribute('cx'));
		const y2 = parseFloat(firstControlPoint.getAttribute('cy'));
		let closureLine = createProxyPathLine( proxyPathGroup, x1, y1, x2, y2 );
		addControlPointEventHandler( firstControlPoint, closureLine, firstLine );
		addControlPointEventHandler( lastControlPoint, previousLine, closureLine );
	    }
	});
    }

    function extendProxyPath( event ) {
	    
	console.log( 'Extending proxy path' );
	const baseSvgElement = $(baseSvgSelector);
	let svgPoint = toSvgPoint( baseSvgElement, event.clientX, event.clientY );

	let referenceElement = getReferenceElementForExtendingProxyPath();
	let newControlPoint = null;
	
	if (  $(referenceElement).hasClass('proxy-point') ) {
	    let proxyPathGroup = $(referenceElement).closest('g.hi-proxy-path');
	    if ( $(proxyPathGroup).attr('hi-proxy-path-type') == 'open' ) {
		if ( $(referenceElement).is(':first-of-type') ) {
		    // TODO: prepend new control point to path
		} else {
		    // TODO: append new control point to path
		}
	    } else {
		// TODO: add new control point by splitting line of "after" line of reference point
	    }
	} else if (  $(referenceElement).hasClass('proxy-line') ) {
	    // TODO: add new control point by splitting reference line
	} else {
	    console.log( 'Unrecognized reference proxy element.' );
	    return;
	}
	
	
	if ( gSvgPathEditData.selectedProxyElement ) {
	} else {
	}

	if ( newControlPoint ) {
	    setSelectedProxyElement( newControlPoint );
	}
    }

    function getReferenceElementForExtendingProxyPath( ) {
	if ( gSvgPathEditData.selectedProxyElement ) {
	    return gSvgPathEditData.selectedProxyElement;
	}
	let lastProxyPath = $(gSvgPathEditData.proxyPathContainer).find('g.hi-proxy-path').last();
	let lastControlPoint = lastProxyPath.find('circle.proxy-point').last();
	return lastControlPoint;
    }
    
    function createProxyPathControlPoint( svg, cx, cy ) {
	const controlPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
	controlPoint.setAttribute('cx', cx);
	controlPoint.setAttribute('cy', cy);
	controlPoint.setAttribute('r', 25);
	controlPoint.setAttribute('fill', 'red');
	controlPoint.setAttribute('class', 'draggable proxy proxy-point');
	controlPoint.setAttribute('vector-effect', 'non-scaling-stroke');
	svg.appendChild(controlPoint);
	return controlPoint;
    }

    function createProxyPathLine( svg, x1, y1, x2, y2 ) {
	const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
	line.setAttribute('x1', x1);
	line.setAttribute('y1', y1);
	line.setAttribute('x2', x2);
	line.setAttribute('y2', y2);
	line.setAttribute('class', 'proxy proxy-line');
	line.setAttribute('stroke', 'red');
	line.setAttribute('stroke-width', '5');
	line.setAttribute('vector-effect', 'non-scaling-stroke');
	$(svg).prepend(line);  // Need control points to draw after lines (else selection is wonky).
	return line;
    }
    
    function addControlPointEventHandler( controlPoint, beforeLine, afterLine ) {
	
	// Drag logic for the control point
	controlPoint.addEventListener('mousedown', function(e) {
            e.preventDefault();
            const offsetX = e.clientX - parseFloat(controlPoint.getAttribute('cx'));
            const offsetY = e.clientY - parseFloat(controlPoint.getAttribute('cy'));
	    
            function onMouseMove(e) {
		const newCx = e.clientX - offsetX;
		const newCy = e.clientY - offsetY;
		controlPoint.setAttribute('cx', newCx);
		controlPoint.setAttribute('cy', newCy);

		// Update the line endpoints to follow control point movement
		if ( beforeLine ) {
                    beforeLine.setAttribute('x2', newCx);
                    beforeLine.setAttribute('y2', newCy);
		}
		if ( afterLine ) {
                    afterLine.setAttribute('x1', newCx);
                    afterLine.setAttribute('y1', newCy);
		}

		setSelectedProxyElement( controlPoint );
            }
	    
            function onMouseUp() {
		document.removeEventListener('mousemove', onMouseMove);
		document.removeEventListener('mouseup', onMouseUp);
            }
	    
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
	});
    }
    
    function collapseSvgPath( pathSvgGroup ) {
	if ( DEBUG ) { console.log( 'Collapse SVG Path', pathSvgGroup ); }

	// zzz adjust path


	/*
    const svg = document.getElementById('my-svg');
    const lines = svg.querySelectorAll('line');
    let newPathData = '';

    // Loop through lines and recombine them into a single path
    lines.forEach(line => {
        const x1 = line.getAttribute('x1');
        const y1 = line.getAttribute('y1');
        const x2 = line.getAttribute('x2');
        const y2 = line.getAttribute('y2');
        newPathData += `M ${x1} ${y1} L ${x2} ${y2} `;
        svg.removeChild(line);  // Remove each line after processing
    });

    controlPoints.forEach(point => svg.removeChild(point));  // Remove control points

    if (selectedPath) {
        selectedPath.setAttribute('d', newPathData.trim());  // Set the new path data
        selectedPath.style.display = '';  // Make the path visible again
    }
*/
	
	
	pathSvgGroup.show();



	gSvgPathEditData = null;
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
