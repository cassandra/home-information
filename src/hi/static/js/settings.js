(function() {

    window.Hi = window.Hi || {};

    const HiSettings = {

	enableAudio: function() {
	    return _enableAudio( );
	},
	disableAudio: function() {
	    return _disableAudio( );
	},
	isAudioEnabled: function() {
	    return _isAudioEnabled( );
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
	Hi.setCookie( name, value );
    }
    
    function getConsoleSetting( name ) {
	return Hi.getCookie( name );
    }
    
    function _enableAudio() {
	setConsoleSetting( AudioStateSettingName, AudioStateEnabled );
	return true;
    }

    function _disableAudio() {
	setConsoleSetting( AudioStateSettingName, AudioStateDisabled );
	return true;
    }

    function _isAudioEnabled() {
	var audioState = getConsoleSetting( AudioStateSettingName );
	if ( audioState && ( audioState == AudioStateDisabled ))
	    return false;
	return true;
    }
    
})();
