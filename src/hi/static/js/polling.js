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
	    
	    for ( let cssClass in respObj[CssClassUpdateMap] ) {
		let elements;
		if ( cssClass in gCssClassElementCache ) {
		    elements = gCssClassElementCache[cssClass];
		} else {
		    elements = $(`.${cssClass}`);
		    gCssClassElementCache[cssClass] = elements;
		}
		let attrMap = respObj[CssClassUpdateMap][cssClass];
		for ( let attrName in attrMap ) {		    
		    let attrValue = attrMap[attrName];
		    elements.each( function() {
			if (this.hasAttribute(attrName)) {
			    let currentValue = $(this).attr(attrName);
			    if ( attrValue && ( currentValue !== String(attrValue) )) {
				$(this).attr( attrName, attrValue );
			    }
			}
		    });
		}
	    }
	}
	catch (e) {
	    console.error( "Exception parsing server response: " + e
			   + " (line="+e.lineNumber+")" );
	}
	finally {
	    gPollingTimer = setTimeout( fetchServerResponse,
					ServerPollingIntervalMs );
	}
    }
    
    function clearPollingTimer() {
	if ( gPollingTimer ) {
	    clearTimeout( gPollingTimer );
	    gPollingTimer = null;
	}
    }

	
})();
