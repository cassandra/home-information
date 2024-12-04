(function() {
    window.Hi = window.Hi || {};

    const HiPolling = {
        init: function() {
	    startPolling();
        },
    };
    
    window.Hi.polling = HiPolling;

    window.addEventListener('load', function() {
	HiPolling.init();
    });

    /*
      POLLING

      - Periodic polling of server to get status and alerts.
    */

    const ServerPollingWatchdogType = 'serverPolling';
    const ServerPollingIntervalMs = 5 * 1000;
    const ServerPollingUrl = '/api/status';
    const CssClassUpdateMap = 'cssClassUpdateMap';
    
    let gPollingTimer = null;
    let gCssClassElementCache = {};
    
    function startPolling() {
	Hi.watchdog.add( ServerPollingWatchdogType, 
			 fetchServerResponse,
			 ServerPollingIntervalMs );
	fetchServerResponse();
    }

    function fetchServerResponse() {
	if ( Hi.DEBUG ) { console.log( "Polling server..." ); }
	clearPollingTimer();

	$.ajaxSuppressLoader = true;
	$.ajax({
	    type: 'GET',
	    url: ServerPollingUrl,

	    complete: function (jqXHR, textStatus) {
		$.ajaxSuppressLoader = false;
	    },
	    success: function( data, status, xhr ) {
		handleServerResponse( data, status, xhr );
		return false;
	    },
	    error: function (xhr, ajaxOptions, thrownError) {
		console.error( `Server polling error [${xhr.status}] : ${thrownError}` );
		return false;
	    } 
	});
    }

    function handleServerResponse( respObj, textStatus, jqXHR ) {
	try {
	    if ( Hi.DEBUG ) { console.log( "Server response: "+JSON.stringify( respObj)); }
	    Hi.watchdog.ok( ServerPollingWatchdogType );
	    clearPollingTimer();
	    handleAttributeUpdates( respObj );
	    
	} catch (e) {
	    console.error( "Exception parsing server response: " + e
			   + " (line="+e.lineNumber+")" );
	    
	} finally {
	    gPollingTimer = setTimeout( fetchServerResponse,
					ServerPollingIntervalMs );
	}
    }

    function handleAttributeUpdates( respObj ) {

	for ( let cssClass in respObj[CssClassUpdateMap] ) {
	    let elements = getElementByCssClass( cssClass );
	    let attrMap = respObj[CssClassUpdateMap][cssClass];
	    for ( let attrName in attrMap ) {		    
		let attrValue = attrMap[attrName];
		elements.each( function() {
		    if (this.hasAttribute(attrName)) {
			let currentValue = $(this).attr(attrName);
			if ( attrValue && ( currentValue !== String(attrValue) )) {
			    $(this).attr( attrName, attrValue );
			}
		    } else {
			// Special cases:
			//    - descendent SELECT tag - assume select value is sensor value
			//    - descendent checkbox - assumes status value 'on' when checked
			//    - descendent DIV tag with status attr - assume attr and text needs updating
			//
			if ( attrName == 'status' ) {
			    $(this).find('select').val( attrValue );
			    
			    $(this).find('input[type="checkbox"]').each( function(index, element) {
				if ( attrValue == 'on' ) {
				    $(element).attr( 'checked', 'true' );
				} else {
				    $(element).removeAttr( 'checked' );
				}
			    });
			    
			    $(this).find('div[status]').each( function(index, element) {
				$(element).attr( attrName, attrValue );
				$(element).text( attrValue );
			    });
			}
		    }
		});
	    }
	}
    }

    function getElementByCssClass( cssClass ) {

	if ( cssClass in gCssClassElementCache ) {
	    const cachedElements = gCssClassElementCache[cssClass];
            const connectedElements = $(cachedElements).filter( function () {
		if ( cssClass == 'hi-entity-state-203' ) { console.log( `Status ${this}=${this.isConnected}` ); }
		return this.isConnected;
            });
            if ( cachedElements.length == connectedElements.length) {
		if ( cssClass == 'hi-entity-state-203' ) { console.log( `Cached: ${cssClass}` ); }
		return connectedElements;
	    }
	}

	if ( cssClass == 'hi-entity-state-203' ) { console.log( `Querying: ${cssClass}` ); }
	
	let elements = $(`.${cssClass}`);
	if ( elements.length > 0 ) {
	    gCssClassElementCache[cssClass] = elements;
	} else {
	    delete gCssClassElementCache[cssClass];
	}
	return elements;
    }
    
    function clearPollingTimer() {
	if ( gPollingTimer ) {
	    clearTimeout( gPollingTimer );
	    gPollingTimer = null;
	}
    }

	
})();
