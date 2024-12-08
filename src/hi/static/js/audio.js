(function() {
    window.Hi = window.Hi || {};

    const HiAudio = {

	WARNING_SIGNAL_NAME: 'warning',
	INFO_SIGNAL_NAME: 'info',
	
        init: function() {
	    startAudioPolling();
        },
        startAudibleSignal: function( signalName ) {
	    _startAudibleSignal( signalName );
        },
	setMaxSignalName: function( signalName ) {
	    return _setMaxSignalName( signalName );
	}
    };
    
    window.Hi.audio = HiAudio;

    window.addEventListener('load', function() {
	HiAudio.init();
    });

    const AudioPollingWatchdogType = 'audioPolling';
    const AudioPollingStartDelayMs = 5 * 1000;
    const AudioPollingIntervalMs = 3 * 60 * 1000;

    let gAudioPollingTimer = null;
    let gCurrentMaxSignalName = null;
    
    function startAudioPolling() {
	Hi.watchdog.add( AudioPollingWatchdogType, 
			 checkAudioStatus,
			 AudioPollingIntervalMs );
	gAudioPollingTimer = setTimeout( checkAudioStatus, AudioPollingStartDelayMs );
    }

    function setAudioPollingTimer() {
	clearAudioPollingTimer();
	gAudioPollingTimer = setTimeout( checkAudioStatus, AudioPollingIntervalMs );
    }

    function clearAudioPollingTimer() {
	if ( gAudioPollingTimer ) {
	    clearTimeout( gAudioPollingTimer );
	    gAudioPollingTimer = null;
	}
    }

    function checkAudioStatus() {
	clearAudioPollingTimer();
	try {
	    Hi.watchdog.ok( AudioPollingWatchdogType );

	    if ( gCurrentMaxSignalName ) {
		if ( Hi.DEBUG ) { console.log( "Audio max signal found." ); }
		_startAudibleSignal( gCurrentMaxSignalName );
	    }
	} catch (e) {
	    console.error( `Exception in audio polling: ${e} (line=${e.lineNumber})` );
	} finally {
	    setAudioPollingTimer();
	}
    }

    const SignalAudioIdPrefix = 'hi-audio-signal';
    const AudibleSignalDurationMs = 5 * 1000;
    
    let gAudibleSignalTimer = null;
    let gActiveAudibleSignalName = null;

    function _setMaxSignalName( signalName ) {
	gCurrentMaxSignalName = signalName;
	return true;
    }
    
    function setAudibleSignalTimer( ) {
	clearAudibleSignalTimer();
	gAudibleSignalTimer = setTimeout( endAudibleSignal, AudibleSignalDurationMs );
    }
    
    function clearAudibleSignalTimer( ) {
	if ( gAudibleSignalTimer ) {
	    clearTimeout( gAudibleSignalTimer );
	    gAudibleSignalTimer = null;
	}
    }

    function getAudioElementId( signalName ) {
	return `${SignalAudioIdPrefix}-${signalName}`;
    }
    
    function _startAudibleSignal( signalName ) {
	if ( Hi.DEBUG ) { console.log( `Starting audio signal = ${signalName}` ); }
	try {
	    stopAudio( );
	    clearAudibleSignalTimer();
	    if ( ! Hi.settings.isAudioEnabled() ) {
		return;
	    }
	    let id = getAudioElementId( signalName );
	    let elem = document.getElementById(id);
	    if ( ! elem ) {
		if ( Hi.DEBUG ) { console.log( `Missing audio tag for ${signalName}` ); }
		return;
	    }
	    else {
		elem.currentTime = 0;
		elem.play();
		gActiveAudibleSignalName = signalName;
		setAudibleSignalTimer();
	    }
	}
	catch (e) {
	    console.error( `Exception starting audible signal: ${e} (line=${e.lineNumber})` );
	}
    }

    function endAudibleSignal( ) {
	stopAudio();
	clearAudibleSignalTimer();
	
	// Always "reset" this so we do not signal too frequently
	setAudioPollingTimer();
    }

    function stopAudio( ) {
	if ( ! gActiveAudibleSignalName ) {
	   return;
	}
	let id = getAudioElementId( gActiveAudibleSignalName );
	let elem = document.getElementById(id);
	if ( elem ) {
	    elem.pause();
	}
	gActiveAudibleSignalName = null;
    }

})();
