(function() {

    const POLL_INTERVAL_MS = 3000;

    const HiSimulator = {

	DEBUG: true,

	setCookie: function( name, value, days = 365, sameSite = 'Lax' ) {
	    return _setCookie( name, value, days, sameSite );
	},
	getCookie: function( name ) {
	    return _getCookie( name );
	},
	submitForm: function( formElement ) {
	    return _submitForm( formElement );
	},
	startStatePolling: function( statesUrl, intervalMs ) {
	    return _startStatePolling( statesUrl, intervalMs );
	},
    };

    window.HiSimulator = HiSimulator;

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

    function _startStatePolling( statesUrl, intervalMs ) {
	if ( ! statesUrl ) { return; }
	const interval = intervalMs || POLL_INTERVAL_MS;
	const poll = function() {
	    $.ajax({
		url: statesUrl,
		dataType: 'json',
		global: false,
		success: function( data ) {
		    if ( data && data.states ) {
			_applyStates( data.states );
		    }
		},
		error: function( jqXHR, textStatus ) {
		    if ( HiSimulator.DEBUG ) {
			console.warn( 'Simulator state poll failed:', textStatus );
		    }
		},
	    });
	};
	setInterval( poll, interval );
    }

    function _applyStates( states ) {
	Object.keys( states ).forEach( function( containerId ) {
	    const container = document.getElementById( containerId );
	    if ( ! container ) { return; }
	    if ( container.contains( document.activeElement )) { return; }
	    _updateStateValue( container, states[containerId] );
	});
    }

    function _updateStateValue( container, value ) {
	const range = container.querySelector( 'input[type="range"][name="value"]' );
	if ( range ) {
	    if ( range.value !== value ) {
		range.value = value;
		const output = range.nextElementSibling;
		if ( output && output.tagName === 'OUTPUT' ) {
		    const formatted = _formatNumericDisplay( value );
		    if ( output.value !== formatted ) { output.value = formatted; }
		}
	    }
	    return;
	}
	const checkbox = container.querySelector( 'input[type="checkbox"][name="value"]' );
	if ( checkbox ) {
	    const desired = _truthy( value );
	    if ( checkbox.checked !== desired ) { checkbox.checked = desired; }
	    return;
	}
	const select = container.querySelector( 'select[name="value"]' );
	if ( select ) {
	    if ( select.value !== value ) { select.value = value; }
	    return;
	}
    }

    function _formatNumericDisplay( value ) {
	const num = parseFloat( value );
	if ( Number.isNaN( num )) { return value; }
	// Mirror Django's |floatformat:"-1" — strip trailing .0 for ints
	return ( num % 1 === 0 ) ? String( num ) : String( num );
    }

    function _truthy( value ) {
	if ( typeof value === 'boolean' ) { return value; }
	const lowered = String( value ).trim().toLowerCase();
	return ( lowered === 'true' || lowered === '1'
		 || lowered === 'on' || lowered === 'yes'
		 || lowered === 'open' || lowered === 'movement' );
    }

    $(document).ready( function() {
	const main = document.querySelector( '.sim-main[data-states-url]' );
	if ( main ) {
	    _startStatePolling( main.getAttribute( 'data-states-url' ));
	}
    });

})();
