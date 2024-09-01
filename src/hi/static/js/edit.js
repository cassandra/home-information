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

    let clickStart = null;
    let clickTimeout = null;
    const doubleClickDelayMs = 300;

    let isDragging = false;
    let dragData = null;
    const dragThreshold = 3;

    let lastMousePosition = { x: 0, y: 0 };
    let itemEditState = {
	currentElement: null,
	mode: 'move',
	scaleStart: 1.0,
	rotateStart: 0.0,
    }
    
    $(document).ready(function() {
	$(document).on('mousedown', locationViewAreaSelector, function(event) {
	    isDragging = false;
	    clickStart = {
		x: event.clientX,
		y: event.clientY,
		time: Date.now()
	    }
	    createDragData( event );
	});
	$(document).on('mousemove', locationViewAreaSelector, function(event) {
	    if ( ! dragData ) {
		return;
	    }
	    const distanceX = Math.abs( event.clientX - clickStart.x );
	    const distanceY = Math.abs( event.clientY - clickStart.y );
	    
	    if ( isDragging || ( distanceX > dragThreshold ) || ( distanceY > dragThreshold )) {
		isDragging = true;
		updateDrag(event);
	    }
	});
	$(document).on('mouseup', locationViewAreaSelector, function(event) {
	    if ( isDragging ) {
		endDrag( event );
		return;
	    }
	    dragData = null;
	    
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
		}, doubleClickDelayMs );
	    }
	});
	$(document).on('mousemove', function(event) {
	    const currentMousePosition = {
		x: event.pageX,
		y: event.pageY
	    };
	    if ( itemEditState.mode == 'scale' ) {
		itemEditScaleUpdate( currentMousePosition );
	    } else if ( itemEditState.mode == 'rotate' ) {
		itemEditRotateUpdate( currentMousePosition );
	    }
		
            lastMousePosition = currentMousePosition;
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

	itemEditState.currentElement = enclosingSvgGroup;
	
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

	if ( ! itemEditState.currentElement ) {
	    return;
	}

	if ( event.key == 's' ) {
	    itemEditRotateAbort();
	    itemEditScaleStart();
	    itemEditState.mode = 'scale';
	    
	} else if ( event.key == 'r' ) {
	    itemEditScaleAbort();
	    itemEditRotateStart();
	    itemEditState.mode = 'rotate';	    
	    
	} else if ( event.key == 'Escape' ) {
	    itemEditScaleAbort();
	    itemEditRotateAbort();
	    itemEditState.mode = 'move';
	    
	} else if ( event.key == 'Enter' ) {
	    if ( itemEditState.mode == 'scale' ) {
		itemEditScaleApply();
	    }
	    else if ( itemEditState.mode == 'rotate' ) {
		itemEditRotateApply();
	    } else {
		return;
	    }
	    itemEditState.mode = 'move';
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
	    
	}
	
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

    function updateSvgTransform( element, scale, translate, rotate ) {
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
    
    function itemEditScaleStart() {
	console.log( 'Scale Start' );
        let transform = itemEditState.currentElement.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );
	itemEditState.scaleStart = scale;
    }

    function itemEditRotateStart() {
        let transform = itemEditState.currentElement.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );
	itemEditState.rotateStart = rotate;
    }

    function itemEditScaleUpdate( currentMousePosition ) {
	console.log( 'Scale Update' );
	const deltaX = currentMousePosition.x - lastMousePosition.x;
	const deltaY = currentMousePosition.y - lastMousePosition.y;
	if (( deltaX <= dragThreshold ) && ( deltaY <= dragThreshold )) {
	    return;
	}
        let transform = itemEditState.currentElement.attr('transform');
	console.log( `T = ${transform}` );
        let { scale, translate, rotate } = getTransformValues( transform );
	console.log( `SCALE = ${scale}, T = ${translate}, R = ${rotate}` );
	const newScale = {
	    x: scale.x + 0.01 * deltaX,
	    y: scale.x + 0.01 * deltaX
	};
	
	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.x / newScale.x;

	updateSvgTransform( itemEditState.currentElement, newScale, translate, rotate );
    }
    
    function itemEditRotateUpdate( currentMousePosition ) {
	const deltaX = currentMousePosition.x - lastMousePosition.x;
	const deltaY = currentMousePosition.y - lastMousePosition.y;
	if (( deltaX <= dragThreshold ) && ( deltaY <= dragThreshold )) {
	    return;
	}
        let transform = itemEditState.currentElement.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );
	rotate.angle = rotate.angle + deltaX;
	updateSvgTransform( itemEditState.currentElement, scale, translate, rotate );
    }
    
    function itemEditScaleApply() {
	console.log( 'Scale Apply' );
	saveSvgPosition( itemEditState.currentElement );
    }

    function itemEditRotateApply() {
	saveSvgPosition( itemEditState.currentElement );
    }
    
    function itemEditScaleAbort() {
	if ( itemEditState.mode != 'scale' ) {
	    return;
	}
	console.log( 'Scale Abort' );
        let transform = itemEditState.currentElement.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );

	const newScale = itemEditState.scaleStart;

	translate.x = translate.x * scale.x / newScale.x;
	translate.y = translate.y * scale.x / newScale.x;
	
	updateSvgTransform( itemEditState.currentElement, newScale, translate, rotate );
    }

    function itemEditRotateAbort() {
	if ( itemEditState.mode != 'rotate' ) {
	    return;
	}
        let transform = itemEditState.currentElement.attr('transform');
        let { scale, translate, rotate } = getTransformValues( transform );
	rotate = itemEditState.rotateStart;
	updateSvgTransform( itemEditState.currentElement, scale, translate, rotate );
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
