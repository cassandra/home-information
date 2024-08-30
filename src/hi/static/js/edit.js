(function() {
    window.Hi = window.Hi || {};

    const HiEdit = {
	editThing: function() {
            return true;
	}
    };
    
    window.Hi.edit = HiEdit;

    const DEBUG = true;
    const clickThreshold = 300; // Adjust the threshold as needed (in milliseconds)
    let dragData = null;
	
    $(document).on('mousedown', function(event) {
	startDrag( event );
	
    });
    $(document).on('mousemove', function(event) {
	updateDrag( event );
    });
    $(document).on('mouseup', function() {
	endDrag( event );
    });
    $(document).on('keydown', function(event) {
        console.log(`Key down: ${event.key}`);
    });
    $(document).on('keyup', function(event) {
        console.log(`Key up: ${event.key}`);
    });

    function startDrag( event ) {
        displayEventInfo( event );
        displayElementInfo( 'Event Target', $(event.target) );

	const enclosingSvgGroup = $(event.target).closest('g');
	if ( enclosingSvgGroup.length > 0 ) {
	    dragData = {};
	    dragData.element = enclosingSvgGroup;
            displayElementInfo( 'Drag Element', dragData.element );
	
	    dragData.startTime = Date.now();

	    dragData.baseSvg = $('#hi-location-view-main > svg');
	    displayElementInfo( 'Base SVG', dragData.baseSvg );

            let transform = dragData.element.attr('transform') || '';
            let { scale, translate, rotate } = getTransformValues( transform );
            let svgPoint = toSvgPoint( dragData.baseSvg[0], event.clientX, event.clientY );

	    dragData.offsetSvgX = (svgPoint.x / scale.x) - translate.x;
	    dragData.offsetSvgY = (svgPoint.y / scale.y) - translate.y;

	    dragData.svgCenter = getSvgCenterPoint( dragData.element, dragData.baseSvg[0] );
	    
	    dragData.scale = scale;
	    dragData.rotate = rotate;

	    if ( DEBUG ) {
		console.log( `Drag Start:
    SVG Cursor Point: ( ${svgPoint.x}, ${svgPoint.y} ), 
    SVG Cursor Offset: ( ${dragData.offsetSvgX}, ${dragData.offsetSvgY} ),
    SVG Center Point: ( ${dragData.svgCenter.x}, ${dragData.svgCenter.y} )`); 
	    }
	}
    }
    
    function updateDrag( event ) {
        if ( dragData == null ) {
	    return;
	}
        displayEventInfo( event );
        displayElementInfo( 'Drag Element', dragData.element );

        let svgPoint = toSvgPoint( dragData.baseSvg[0], event.clientX, event.clientY );

	let scale = dragData.scale;
	let rotate = dragData.rotate
	
        let newX = (svgPoint.x / scale.x) - dragData.offsetSvgX;
        let newY = (svgPoint.y / scale.y) - dragData.offsetSvgY;

        let transform = dragData.element.attr('transform') || '';

        let newTransform = `scale(${scale.x} ${scale.y}) translate(${newX}, ${newY}) rotate(${rotate.angle}, ${rotate.cx}, ${rotate.cy})`;

        dragData.element.attr('transform', newTransform);	    

	dragData.svgCenter = getSvgCenterPoint( dragData.element, dragData.baseSvg[0] );
	
	if ( DEBUG ) {
	    console.log( `Drag Update:
    SVG Cursor Point: ( ${svgPoint.x}, ${svgPoint.y} ),
    TRANSFORM Result: ${newTransform},
    SVG Center Point: ( ${dragData.svgCenter.x}, ${dragData.svgCenter.y} )`); 
	}
    }
    
    function endDrag( event ) {
        if ( dragData == null ) {
	    return;
	}
	
        displayEventInfo( event );
        displayElementInfo( 'Drag Element', dragData.element );
	
	updateDrag( event );

	let dragEndTime = Date.now();
	const elapsedTime = dragEndTime - dragData.startTime;
	if (elapsedTime <= clickThreshold) {
	    console.log( `CLICK: ${elapsedTime}` );
	}
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
            }
	}

	if ( DEBUG ) {
	    console.log( `TRANSFORM:
    Raw: ${transform},
    Parsed: scale=${JSON.stringify(scale)} translate=${JSON.stringify(translate)} rotate=${JSON.stringify(rotate)}` );
	}
	
	return { scale, translate, rotate };
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
        let point = svgElement.createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( svgElement.getScreenCTM().inverse());
    }
    
    function displayEventInfo( event ) {
	if ( ! DEBUG ) { return; }
	if ( ! event ) {
            console.log( 'No element to display info for.' );
	    return;
	}
        console.log( `Event: 
    Type: ${event.type}, 
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
