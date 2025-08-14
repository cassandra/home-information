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
	},
	hasShownPermissionGuidance: function() {
	    return _hasShownPermissionGuidance( );
	},
	markPermissionGuidanceShown: function() {
	    return _markPermissionGuidanceShown( );
	},
	enableSleepMode: function() {
	    return _enableSleepMode( );
	},
	disableSleepMode: function() {
	    return _disableSleepMode( );
	}
    };
    
    window.Hi.settings = HiSettings;

    /*
      SETTINGS

      - Adjustable settings relevant for the console.
    */

    const SleepOverlaySelector = '#hi-sleep-overlay';
    const AudioStateSettingName = 'audioState';
    const AudioStateEnabled = 'enabled';
    const AudioStateDisabled = 'disabled';
    const PermissionGuidanceShownSettingName = 'audioPermissionGuidanceShown';
    const PermissionGuidanceShownValue = 'true';

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

    function _enableSleepMode() {
	let sleepOverlay = $(SleepOverlaySelector);
	$(sleepOverlay).show();
	$(sleepOverlay).off( 'click').on('click', Hi.settings.disableSleepMode );
    }
    function _disableSleepMode() {
	$(SleepOverlaySelector).hide();
    }

    function _hasShownPermissionGuidance() {
	var guidanceShown = getConsoleSetting( PermissionGuidanceShownSettingName );
	return guidanceShown === PermissionGuidanceShownValue;
    }
    
    function _markPermissionGuidanceShown() {
	setConsoleSetting( PermissionGuidanceShownSettingName, PermissionGuidanceShownValue );
	return true;
    }
    
})();