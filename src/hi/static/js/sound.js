(function() {
    window.Hi = window.Hi || {};

    const HiSound = {
        startAudibleSignal: function( signalName ) {
	    _startAudibleSignal( signalName );
        },
    };
    
    window.Hi.sound = HiSound;

    function _startAudibleSignal( signalName ) {
	if ( Hi.DEBUG ) { console.log( `Starting audible signal: ${signalName}` ); }

	
	// TBD
	
    }
    
})();
