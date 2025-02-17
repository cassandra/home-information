(function() {
    
    const Hi = {

	DEBUG: true,
	isEditMode: ( gHiViewMode == 'edit' ),  // Set by server to keep front-end in sync with back-end
	LOCATION_VIEW_AREA_SELECTOR: '#hi-location-view-main',
	LOCATION_VIEW_SVG_CLASS: 'hi-location-view-svg',
	LOCATION_VIEW_SVG_SELECTOR: '.hi-location-view-svg',
	LOCATION_VIEW_BASE_SELECTOR: '.hi-location-view-base',
	BASE_SVG_SELECTOR: '#hi-location-view-main > svg',
	SVG_ICON_CLASS: 'hi-svg-icon',
	SVG_PATH_CLASS: 'hi-svg-path',
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

	const startAngle = Math.atan2( startVectorY, startVectorX );
	const endAngle = Math.atan2( endVectorY, endVectorX );

	let angleDifference = endAngle - startAngle;

	// Normalize the angle to be between -π and π
	if ( angleDifference > Math.PI ) {
            angleDifference -= 2 * Math.PI;
	} else if ( angleDifference < -Math.PI ) {
            angleDifference += 2 * Math.PI;
	}

	const angleDifferenceDegrees = angleDifference * ( 180 / Math.PI );

	return angleDifferenceDegrees;
    }

    function _normalizeAngle(angle) {
	return (angle % 360 + 360) % 360;
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
            let viewBox = $(element).attr( 'viewBox' );
	    if ( viewBox != null ) {
		svgStr = `Viewbox: ${viewBox}`;
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
