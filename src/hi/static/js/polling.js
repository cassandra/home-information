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
    const PollingErrorNotifyTimeMs = 15 * 1000;
    const ServerErrorMessageSelector = '#hi-server-error-msg';
    const ServerPollingUrl = '/api/status';
    const ServerStartTimestampAttr = 'startTimestamp';
    const ServerTimestampAttr = 'timestamp';
    const LastServerTimestampParam = 'lastTimestamp';
    const CssClassUpdateMap = 'cssClassUpdateMap';
    
    let gPollingTimer = null;
    let gCssClassElementCache = {};
    let gLastServerPollSuccessTime = (new Date()).getTime();
    let gIsServerErrorShowing = false;
    let gLastStartServerDate = null;
    let gLastServerDate = null;
    
    function startPolling() {
	Hi.watchdog.add( ServerPollingWatchdogType, 
			 fetchServerResponse,
			 ServerPollingIntervalMs );
	fetchServerResponse();
    }

    function fetchServerResponse() {
	if ( Hi.DEBUG ) { console.log( "Polling server..." ); }
	clearPollingTimer();

	let url = ServerPollingUrl;
	if ( gLastServerDate ) {
	    const lastTimestampString = gLastServerDate.toISOString();
	    url += `?${LastServerTimestampParam}=${lastTimestampString}`;
	}
	
	$.ajaxSuppressLoader = true;
	$.ajax({
	    type: 'GET',
	    url: url,

	    complete: function (jqXHR, textStatus) {
		$.ajaxSuppressLoader = false;
	    },
	    success: function( data, status, xhr ) {
		try {
		    Hi.watchdog.ok( ServerPollingWatchdogType );
		    gLastServerPollSuccessTime = (new Date()).getTime();
		    handleServerResponse( data, status, xhr );
		    return false;

		} catch (e) {
		    console.error( `Exception parsing server response: ${e} (line=${e.lineNumber})` );
		} finally {
		    gPollingTimer = setTimeout( fetchServerResponse, ServerPollingIntervalMs );
		}
	    },
	    error: function (xhr, ajaxOptions, thrownError) {
		try {
		    Hi.watchdog.ok( ServerPollingWatchdogType );
		    console.error( `Server polling error [${xhr.status}] : ${thrownError}` );
		    handlePollingError();
		    return false;
		} catch (e) {
		    console.error( `Exception handling polling error: ${e} (line=${e.lineNumber})` );
		} finally {
		    gPollingTimer = setTimeout( fetchServerResponse, ServerPollingIntervalMs );
		}
	    } 
	});
    }

    function handleServerResponse( respObj, textStatus, jqXHR ) {
	if ( Hi.DEBUG ) { console.log( "Server response: "+JSON.stringify( respObj)); }

	doServerStartTimeCheck( respObj );
	
	if ( ServerTimestampAttr in respObj ) {
	    gLastServerDate = new Date( respObj[ServerTimestampAttr] );
	}
	
	if ( CssClassUpdateMap in respObj ) {
	    handleCssClassUpdates( respObj[CssClassUpdateMap] );
	}
    }

    function doServerStartTimeCheck( respObj ) {
	if ( ServerStartTimestampAttr in respObj ) {
	    let startServerDate = new Date( respObj[ServerStartTimestampAttr] );
	    if ( gLastStartServerDate ) {
		if ( startServerDate.getTime() != gLastStartServerDate.getTime() ) {
		    if ( Hi.DEBUG ) { console.log( "Server restart detected. Reloading page." ); }
		    gLastStartServerDate = startServerDate;
		    location.reload(true);
		}
	    } else {
		gLastStartServerDate = startServerDate;
	    }
	}
    }
    
    function handleCssClassUpdates( updateMap ) {

	for ( let cssClass in updateMap ) {
	    let elements = getElementByCssClass( cssClass );
	    let attrMap = updateMap[cssClass];
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
		return this.isConnected;
            });
            if ( cachedElements.length == connectedElements.length) {
		return connectedElements;
	    }
	}

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

    function handlePollingError() {
	var nowTime = (new Date()).getTime();
	var elapsedMs = nowTime - gLastServerPollSuccessTime;
	if ( Hi.DEBUG ) { console.log( `Polling error elapsedMs=${elapsedMs}` ); }
	
	if ( elapsedMs >= PollingErrorNotifyTimeMs ) {
	    notifyServerError();
	}
    }

    function notifyServerError() {
	if ( gIsServerErrorShowing ) {
	    return;
	}
	$(ServerErrorMessageSelector).show();
	gIsServerErrorShowing = true;
	Hi.sound.startAudibleSignal( "warning" );
    }

    function clearServerError() {
	if ( ! gIsServerErrorShowing ) {
	    return;
	}
	$(ServerErrorMessageSelector).hide();
	gIsServerErrorShowing = false;
	Hi.sound.startAudibleSignal( "info" );
    }

})();
