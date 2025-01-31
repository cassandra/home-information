(function() {
    
    const Hi = {

	DEBUG: true,
	isEditMode: ( gHiViewMode == 'edit' ),  // Set by server to keep front-end in sync with back-end
	LOCATION_VIEW_AREA_SELECTOR: '#hi-location-view-main',
	LOCATION_VIEW_SVG_CLASS: 'hi-location-view-svg',
	LOCATION_VIEW_SVG_SELECTOR: '.hi-location-view-svg',
	LOCATION_VIEW_BASE_SELECTOR: '.hi-location-view-base',
	BASE_SVG_SELECTOR: '#hi-location-view-main > svg',
	HIGHLIGHTED_CLASS: 'highlighted',
	ATTRIBUTE_CONTAINER_SELECTOR: '.hi-attribute',
	FORM_FIELD_CONTAINER_SELECTOR: '.input-group',
	SVG_ACTION_STATE_ATTR_NAME: 'action-state',

	DATA_TYPE_ATTR: 'data-type',
	DATA_TYPE_ICON_VALUE: 'svg-icon',
	DATA_TYPE_PATH_VALUE: 'svg-path',
	
	API_LOCATION_ITEM_DETAILS_URL: '/location/item/details',
	API_LOCATION_ITEM_INFO_URL: '/location/item/info',
	ENTITY_STATE_VALUE_CHOICES_URL_PREFIX: '/edit/entity/state/values',
	
	generateUniqueId: function() {
	    return _generateUniqueId();
	},
	setCookie: function( name, value, days = 365, sameSite = 'Lax' ) {
	    return _setCookie( name, value, days, sameSite );
	},
	getCookie: function( name ) {
	    return _getCookie( name );
	},
	submitForm: function( formElement ) {
	    return _submitForm( formElement );
	},
	togglePasswordField: function( toggleCheckbox ) {
	    return _togglePasswordField( toggleCheckbox );
	},
	setEntityStateValueSelect: function( valueFieldId, instanceName, instanceId ) {
	    return _setEntityStateValueSelect( valueFieldId, instanceName, instanceId );
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

    function _setCookie( name, value, days, sameSite ) {
	const expires = new Date();
	expires.setTime( expires.getTime() + days * 24 * 60 * 60 * 1000 );
	const secureFlag = sameSite === 'None' ? '; Secure' : '';
	document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires.toUTCString()}; path=/; SameSite=${sameSite}${secureFlag}`;
	return true;
    }

    function _getCookie( name ) {
	const nameEQ = `${encodeURIComponent(name)}=`;
	const cookies = document.cookie.split(';'); // SPlit into key-pairs
	for ( let i = 0; i < cookies.length; i++ ) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith( nameEQ )) {
		return decodeURIComponent( cookie.substring( nameEQ.length ));
            }
	}
	return null;	
    }
    
    function _submitForm( formElement ) {
	let form = $(formElement).closest('form');
	if ( Hi.DEBUG ) { console.debug( 'Submitting form:', formElement, form ); }
	$(form).submit();
    }
    
    function _togglePasswordField( toggleCheckbox ) {

        let passwordField = $(toggleCheckbox).closest(Hi.FORM_FIELD_CONTAINER_SELECTOR).find('input[type="password"], input[type="text"]');
        if ( toggleCheckbox.checked ) {
            passwordField.attr('type', 'text');
	    $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Hide');
        } else {
            passwordField.attr('type', 'password');
	    $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Show');
        }
    }

    function _setEntityStateValueSelect( valueFieldId, instanceName, instanceId ) {
	$.ajax({
	    type: 'GET',
	    url: `${Hi.ENTITY_STATE_VALUE_CHOICES_URL_PREFIX}/${instanceName}/${instanceId}`,

	    success: function( data, status, xhr ) {
		const choices_list = data;
		const valueElement = $(`#${valueFieldId}`);
		const valueElementId = $(valueElement).attr('id');
		const valueElementName = $(valueElement).attr('name');

		if (choices_list.length > 0) {
		    const selectElement = $('<select>')
			  .attr( 'id', valueElementId )
			  .attr( 'name', valueElementName );

		    selectElement.append( $('<option>').val('').text('------'));
		    choices_list.forEach( choice => {
			const [value, label] = choice;
			selectElement.append( $('<option>').val(value).text(label) );
		    });
		    valueElement.replaceWith(selectElement);
		} else {
		    const inputElement = $('<input>')
			  .attr( 'type', 'text' )
			  .attr( 'id', valueElementId )
			  .attr( 'name', valueElementName );
		    valueElement.replaceWith(inputElement);
		}
		return false;
	    },
	    error: function (xhr, ajaxOptions, thrownError) {
		console.error( `Fetch entity state choices error [${xhr.status}] : ${thrownError}` );
		return false;
	    } 
	});
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
	    return { x: x, y: y, width: width, height: height };
	}
        let viewBoxValueJquery = $(svgElement).attr( attrName );
	let viewBoxValue = $(svgElement)[0].getAttribute( attrName );

	if ( viewBoxValue != viewBoxValueJquery ) {
	    console.warning( `Inconsistent SVG viewBox: jQuery=${viewBoxValueJquery}, DOM=${viewBoxValue}` );
	}
	
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
	    let viewBox = _getSvgViewBox( element );
	    if ( x != null ) {
		svgStr = `Viewbox: ( ${viewBox.x}, ${viewBox.y}, ${viewBox.width}, ${viewBox.height} )`;
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
