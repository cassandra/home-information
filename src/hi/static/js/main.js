(function() {
    
    const Hi = {

	DEBUG: true,
	isEditMode: ( gHiViewMode == 'edit' ),  // Set by server to keep front-end in sync with back-end
	LOCATION_VIEW_AREA_SELECTOR: '#hi-location-view-main',
	LOCATION_VIEW_SVG_CLASS: 'hi-location-view',
	BASE_SVG_SELECTOR: '#hi-location-view-main > svg',
	HIGHLIGHTED_CLASS: 'highlighted',
	SVG_ACTION_STATE_ATTR_NAME: 'action-state',

	DATA_TYPE_ATTR: 'data-type',
	DATA_TYPE_ICON_VALUE: 'svg-icon',
	DATA_TYPE_PATH_VALUE: 'svg-path',
	API_SHOW_DETAILS_URL: '/edit/details',
	
	generateUniqueId: function() {
	    return _generateUniqueId();
	},
	getScreenCenterPoint: function( element ) {
	    return _getScreenCenterPoint( element );
	},
	getRotationAngle: function( centerX, centerY, startX, startY, endX, endY ) {
	    return _getRotationAngle( centerX, centerY, startX, startY, endX, endY );
	},
	normalizeAngle: function(angle) {
	    return _normalizeAngle(angle);
	},
	getSvgViewBox: function( svgElement ) {
	    return _getSvgViewBox( svgElement );
	},
	getExtentsSvgViewBox: function( svgElement ) {
	    return _getExtentsSvgViewBox( svgElement );
	},
	getSvgCenterPoint: function( element, svgElement ) {
	    return _getSvgCenterPoint( element, svgElement );
	},
	getPixelsPerSvgUnit: function( svgElement ) {
	    return _getPixelsPerSvgUnit( svgElement );
	},
	toSvgPoint: function( svgElement, clientX, clientY) {
	    return _toSvgPoint( svgElement, clientX, clientY);
	},
	getSvgTransformValues: function( transformAttrStr ) {
	    return _getSvgTransformValues( transformAttrStr );
	},
	displayEventInfo: function ( label, event ) {
	    return _displayEventInfo( label, event );
	},
	displayElementInfo: function( label, element ) {
	    return _displayElementInfo( label, element );
	}
	
    };
    
    window.Hi = Hi;

    function _generateUniqueId() {
	return 'id-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    }

    function _getScreenCenterPoint( element ) {
	try {
            let rect = $(element)[0].getBoundingClientRect();
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
        
    function _getRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

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

    function _normalizeAngle(angle) {
	return (angle % 360 + 360) % 360;
    }

    function _getSvgViewBox( svgElement, attrName = 'viewBox' ) {
	let x = null;
	let y = null;
	let width = null;
	let height = null;
	
	if (svgElement.length < 1 ) {
	    return { x, y, width, height };
	}
        let viewBoxValue = $(svgElement).attr( attrName );
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

    function _getExtentsSvgViewBox( svgElement ) {
	// Hi-specific attribute used for pan, zoom and edit operations.
	return _getSvgViewBox( svgElement, 'extents' );
    }
    
    function _getSvgCenterPoint( element, svgElement ) {

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
        
    function _getPixelsPerSvgUnit( svgElement ) {
	let ctm = $(svgElement)[0].getScreenCTM();
	return {
	    scaleX: ctm.a,
	    scaleY: ctm.d
	};
    }

    function _toSvgPoint( svgElement, clientX, clientY) {
        let point = $(svgElement)[0].createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( $(svgElement)[0].getScreenCTM().inverse() );
    }
    
    function _getSvgTransformValues( transformAttrStr ) {
	let scale = { x: 1, y: 1 }, rotate = { angle: 0, cx: 0, cy: 0 }, translate = { x: 0, y: 0 };

	let scaleMatch = transformAttrStr.match(/scale\(([^)]+)\)/);
	if (scaleMatch) {
	    let scaleValues = scaleMatch[1].trim().split(/[ ,]+/).map(parseFloat);
	    scale.x = scaleValues[0];
	    if ( scaleValues.length == 1 ) {
		scale.y = scale.x;
	    } else {
		scale.y = scaleValues[1];
	    }
	}

	let translateMatch = transformAttrStr.match(/translate\(([^)]+)\)/);
	if (translateMatch) {
            let [x, y] = translateMatch[1].trim().split(/[ ,]+/).map(parseFloat);
            translate.x = x;
            translate.y = y;
	}

	let rotateMatch = transformAttrStr.match(/rotate\(([^)]+)\)/);
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
    Raw: ${transformAttrStr},
    Parsed: scale=${JSON.stringify(scale)} translate=${JSON.stringify(translate)} rotate=${JSON.stringify(rotate)}` );
	}
	
	return { scale, translate, rotate };
    }

    function _displayEventInfo ( label, event ) {
	if ( ! Hi.DEBUG ) { return; }
	if ( ! event ) {
	    console.log( 'No element to display info for.' );
	    return;
	}
        console.log( `${label} Event: 
    Type: ${event.type}, 
    Key: ${event.key},
    KeyCode: ${event.keyCode},
    Pos: ( ${event.clientX}, ${event.clientY} )` );
    }

    function _displayElementInfo( label, element ) {
	if ( ! Hi.DEBUG ) { return; }
	if ( ! element ) {
	    console.log( 'No element to display info for.' );
	    return;
	}
	const elementTag = $(element).prop('tagName');
	const elementId = $(element).attr('id') || 'No ID';
	const elementClasses = $(element).attr('class') || 'No Classes';
	
	let rectStr = 'No Bounding Rect';
	try {
	    let rect = $(element)[0].getBoundingClientRect();
	    if ( rect ) {
		rectStr = `Dim: ${rect.width}px x ${rect.height}px,
    Pos: left=${rect.left}px, top=${rect.top}px`;
	    }
	} catch (e) {
	}
	
	let offsetStr = 'No Offset';
	const offset = $(element).offset();
	if ( offset ) {
	    offsetStr = `Offset: ( ${offset.left}px,  ${offset.top}px )`;
	}
	
	let svgStr = 'Not an SVG';
	if ( elementTag == 'svg' ) {
	    let { x, y, width, height } = _getSvgViewBox( element );
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
