(function() {
    
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
	    
})();    
