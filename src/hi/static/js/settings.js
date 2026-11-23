(function() {

    window.Hi = window.Hi || {};

    const HiSettings = {

		enableAudio: function() {
			return _enableAudio();
		},

		disableAudio: function() {
			return _disableAudio();
		},

		isAudioEnabled: function() {
			return _isAudioEnabled();
		},

		hasShownPermissionGuidance: function() {
			return _hasShownPermissionGuidance();
		},

		markPermissionGuidanceShown: function() {
			return _markPermissionGuidanceShown();
		},

		enableSleepMode: function() {
			return _enableSleepMode();
		},

		disableSleepMode: function() {
			return _disableSleepMode();
		},
		
	};
    
    window.Hi.settings = HiSettings;

    /*
      SETTINGS

      - Adjustable settings relevant for the console.
    */

    const SleepOverlaySelector = '#hi-sleep-overlay';
    const SleepingClass = 'sleeping';
    const SleepModeCookieValue = 'on';  // Only the cookie's presence matters.
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

	function _hasShownPermissionGuidance() {
		var guidanceShown = getConsoleSetting( PermissionGuidanceShownSettingName );
		return guidanceShown === PermissionGuidanceShownValue;
    }
    
    function _markPermissionGuidanceShown() {
		setConsoleSetting( PermissionGuidanceShownSettingName, PermissionGuidanceShownValue );
		return true;
    }

    // Delegated so it also wakes an overlay the server rendered as sleeping.
    $(document).on( 'click', SleepOverlaySelector, function() {
		Hi.settings.disableSleepMode();
    });

    function _enableSleepMode() {
		Hi.setCookie( Hi.SLEEP_MODE_COOKIE_NAME, SleepModeCookieValue );
		$(SleepOverlaySelector).addClass( SleepingClass );
    }

    function _disableSleepMode() {
		Hi.deleteCookie( Hi.SLEEP_MODE_COOKIE_NAME );
		$(SleepOverlaySelector).removeClass( SleepingClass );
    }

})();