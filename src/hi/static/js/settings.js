(function() {

    window.Hi = window.Hi || {};

    const HiSettings = {
	enableAudio: function() {
	    _enableAudio( );
	},
	disableAudio: function() {
	    _disableAudio( );
	},
	isAudioEnabled: function() {
	    _isAudioEnabled( );
	}
    };

    window.Hi.settings = HiSettings;

    /*
      SETTINGS

      - Adjustable settings relevant for the console.
    */

    const AudioStateSettingName = 'audioState';
    const AudioStateEnabled = 'enabled';
    const AudioStateDisabled = 'disabled';
    
    function setConsoleSetting( name, value ) {
	$.cookie( name, value, { path: '/' } );
    }
    
    function getConsoleSetting( name ) {
	return $.cookie( name );
    }
    
    function _enableAudio() {
	setConsoleSetting( AudioStateSettingName, AudioStateEnabled );
    }

    function _disableAudio() {
	setConsoleSetting( AudioStateSettingName, AudioStateDisabled );
    }
    
    function _isAudioEnabled() {
	var audioState = getConsoleSetting( AudioStateSettingName );
	if ( audioState && ( audioState == AudioStateDisabled ))
	    return false;
	return true;
    }
    
})();
