(function() {
    
    const Hi = {

	DEBUG: true,
	LOCATION_VIEW_AREA_SELECTOR: '#hi-location-view-main',
	LOCATION_VIEW_SVG_CLASS: 'hi-location-view',
	BASE_SVG_SELECTOR: '#hi-location-view-main > svg',
	HIGHLIGHTED_CLASS: 'highlighted',
	DATA_TYPE_ATTR: 'data-type',
	DATA_TYPE_ICON_VALUE: 'svg-icon',
	DATA_TYPE_PATH_VALUE: 'svg-path',
	API_SHOW_DETAILS_URL: '/edit/details',
	
	generateUniqueId: function() {
	    return _generateUniqueId();
	},
	getSvgViewBox: function( svgElement ) {
	    return _getSvgViewBox( svgElement );
	},
	getPixelsPerSvgUnit: function( svgElement ) {
	    return _getPixelsPerSvgUnit( svgElement );
	},
	toSvgPoint: function( svgElement, clientX, clientY) {
	    return _toSvgPoint( svgElement, clientX, clientY);
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

    function _getSvgViewBox( svgElement ) {
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
    
    function _getPixelsPerSvgUnit( svgElement ) {
	let ctm = svgElement[0].getScreenCTM();
	return {
	    scaleX: ctm.a,
	    scaleY: ctm.d
	};
    }

    function _toSvgPoint( svgElement, clientX, clientY) {
        let point = svgElement[0].createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        return point.matrixTransform( svgElement[0].getScreenCTM().inverse() );
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
