(function() {
    window.Hi = window.Hi || {};
    
    const HiSvgUtils = {
	overlayData: function( svgOverlayData ) {

	    const baseSvgData = getBaseSvgData( svgOverlayData.base_html_id );
	    
	},
	getSvgViewBox: function( svgElement ) {
	    return _getSvgViewBox( svgElement );
	},
	setSvgViewBox: function( svgElement, newX, newY, newWidth, newHeight ) {
	    return _setSvgViewBox( svgElement, newX, newY, newWidth, newHeight );
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
	}
    };
    
    window.Hi.svgUtils = HiSvgUtils;

    function getBaseSvgData( htmlId ) {

	const $baseSvg = $('#' + htmlId + ' svg' );

	const bbox = $baseSvg[0].getBoundingClientRect();
	const viewBox = _getSvgViewBox( $baseSvg );	

	const scaleX = bbox.width / viewBox.width;
	const scaleY = bbox.height / viewBox.height;
	
	return {
	    htmlBoundingBox : bbox,
	    svgViewBox : viewBox,
	    scaleX : scaleX,
	    scaleY : scaleY
	};
    }

    function _getSvgViewBox( svgElement, attrName = 'viewBox' ) {
	let x = null;
	let y = null;
	let width = null;
	let height = null;

	if (svgElement.length < 1 ) {
	    return { x: x, y: y, width: width, height: height };
	}
        let viewBoxValue = $(svgElement).attr( attrName );
	if ( viewBoxValue === null || viewBoxValue === undefined ) {
            console.error( "No viewBox value found.", svgElement );
	    return { x: x, y: y, width: width, height: height };
	}
	
	let viewBoxArray = viewBoxValue.split(' ').map(Number);

	if (viewBoxArray.length !== 4 || viewBoxArray.some(isNaN)) {
            console.error( `Invalid viewBox attribute: ${viewBoxValue}`, svgElement );
	    return { x: x, y: y, width: width, height: height };
	}
	
	x = viewBoxArray[0];
	y = viewBoxArray[1];
	width = viewBoxArray[2];
	height = viewBoxArray[3];
	
	return { x: x, y: y, width: width, height: height };
    }

    function _setSvgViewBox( svgElement, newX, newY, newWidth, newHeight ) {
	if ( $(svgElement).length < 1 ) {
            console.error("SVG element is null or undefined.");
            return;
	}
	if ( typeof newX !== 'number' || isNaN(newX)) {
            console.error("newX is not a valid number:", newX);
            return;
	}
	if ( typeof newY !== 'number' || isNaN(newY)) {
            console.error("newY is not a valid number:", newY);
            return;
	}
	if ( typeof newWidth !== 'number' || isNaN(newWidth) || newWidth <= 0) {
            console.error("newWidth is not a valid positive number:", newWidth);
            return;
	}
	if ( typeof newHeight !== 'number' || isNaN(newHeight) || newHeight <= 0) {
            console.error("newHeight is not a valid positive number:", newHeight);
            return;
	}

	const svgViewBoxStr = `${newX} ${newY} ${newWidth} ${newHeight}`;
	$(svgElement).attr('viewBox', svgViewBoxStr );	    	
    }
    
    function _getExtentsSvgViewBox( svgElement ) {
	// Hi-specific attribute used for pan, zoom and edit operations.
	return _getSvgViewBox( svgElement, 'extents' );
    }
    
    function _getSvgCenterPoint( element, svgElement ) {

	try {
            let rect = $(element)[0].getBoundingClientRect();
	    if ( rect ) {
		const screenCenterX = rect.left + ( rect.width / 2.0 );
		const screenCenterY = rect.top + ( rect.height / 2.0 );
		return _toSvgPoint( svgElement, screenCenterX, screenCenterY );
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

    function _getSvgTransformValues(transformAttrStr) {
	const defaultValues = {
            scale: { x: 1, y: 1 },
            rotate: { angle: 0, cx: 0, cy: 0 },
            translate: { x: 100, y: 100 }, // Keep it somewhat in view. At (0,0) is can get lost
	};

	if ( ! transformAttrStr ) {
            return defaultValues;
	}

	const transform = { ...defaultValues }; // Create a copy of default values

	const transformRegex = /((scale|translate|rotate)\(([^)]+)\))/g;
	let match;

	while (( match = transformRegex.exec( transformAttrStr ))) {
            const type = match[2];
            const valuesStr = match[3].trim();

            switch (type) {
            case 'scale':
                const scaleValues = valuesStr.split(/[,\s]+/).map(parseFloat);
                transform.scale.x = scaleValues[0];
                transform.scale.y = scaleValues[1] === undefined ? scaleValues[0] : scaleValues[1];
                break;
            case 'translate':
                const translateValues = valuesStr.split(/[,\s]+/).map(parseFloat);
                transform.translate.x = translateValues[0];
                transform.translate.y = translateValues[1];
                break;
            case 'rotate':
                const rotateValues = valuesStr.split(/[,\s]+/).map(parseFloat);
                transform.rotate.angle = rotateValues[0];
                transform.rotate.cx = rotateValues[1] || 0;
                transform.rotate.cy = rotateValues[2] || 0;
                break;
            }
	}

	if (Hi.DEBUG) {
            console.log(`TRANSFORM:
        Raw: ${transformAttrStr},
        Parsed: scale=${JSON.stringify(transform.scale)} translate=${JSON.stringify(transform.translate)} rotate=${JSON.stringify(transform.rotate)}`);
	}

	return transform;
    }
    
    function _getSvgTransformValuesOriginal( transformAttrStr ) {
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
    
})();
