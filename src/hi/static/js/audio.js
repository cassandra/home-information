(function() {
    window.Hi = window.Hi || {};

    const HiAudio = {
        // Constants used by status.js
        WARNING_SIGNAL_NAME: 'ConsoleWarning',
        INFO_SIGNAL_NAME: 'ConsoleInfo',
        
        // Audio playback methods used by status.js
        startAudibleSignal: function( signalName ) {
            _startAudibleSignal( signalName );
        },
        setActiveSignalName: function( signalName ) {
            return _setActiveSignalName( signalName );
        },
        clearAudibleSignal: function() {
            _clearAudibleSignal();
        },
        
        // Audio control UI methods used by audio_control.html
        updateAudioButtonState: function() {
            return _updateAudioButtonState();
        },
        handleAudioButtonClick: function() {
            return _handleAudioButtonClick();
        },
        
        // Initialization
        init: function() {
            startAudioPolling();
        }
    };
    
    window.Hi.audio = HiAudio;

    window.addEventListener('load', function() {
        HiAudio.init();
        _setupAudioErrorHandlers();
    });

    const AudioPollingWatchdogType = 'audioPolling';
    const AudioPollingStartDelayMs = 5 * 1000;
    const AudioPollingIntervalMs = 3 * 60 * 1000;

    let gAudioPollingTimer = null;
    let gActiveSignalName = null;
    
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

            if ( gActiveSignalName ) {
                _startAudibleSignal( gActiveSignalName );
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

    function _setActiveSignalName( signalName ) {
        if (Hi.DEBUG) { console.log(`Setting active audio signal: ${signalName}`); }
        gActiveSignalName = signalName;
        return true;
    }

    function _clearAudibleSignal() {
        gActiveSignalName = null;
        endAudibleSignal();
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
                if ( Hi.DEBUG ) { console.log( `Audio disabled, not playing signal: ${signalName}` ); }
                return;
            }
            let id = getAudioElementId( signalName );
            if ( Hi.DEBUG ) { console.log( `Looking for audio element with ID: ${id}` ); }
            let elem = document.getElementById(id);
            if ( ! elem ) {
                if ( Hi.DEBUG ) { console.log( `Missing audio tag for ${signalName}` ); }
                return;
            }
            if ( Hi.DEBUG ) { console.log( `Found audio element for ${signalName}` ); }
            
            // Check if audio file loaded successfully
            if (elem.readyState === 0) {
                console.error( `Audio file not loaded for ${signalName}` );
                return;
            }
            
            // Check for audio loading errors
            if (elem.error) {
                console.error( `Audio file error for ${signalName}: ${elem.error.message}` );
                return;
            }
            else {
                elem.currentTime = 0;
                // Handle autoplay policy restrictions
                const playPromise = elem.play();
                if ( Hi.DEBUG ) { console.log( `Attempting to play audio element: ${id}` ); }
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        // Audio playback started successfully
                        if ( Hi.DEBUG ) { console.log( `Audio playback started successfully: ${signalName}` ); }
                        gActiveAudibleSignalName = signalName;
                        setAudibleSignalTimer();
                    }).catch(error => {
                        // Autoplay was prevented
                        if (error.name === 'NotAllowedError') {
                            if ( Hi.DEBUG ) { console.log( `Audio autoplay blocked for ${signalName}` ); }
                            _showPermissionGuidanceIfNeeded();
                        } else {
                            console.error( `Audio playback error for ${signalName}: ${error}` );
                        }
                    });
                } else {
                    // Fallback for older browsers that don't return a Promise
                    gActiveAudibleSignalName = signalName;
                    setAudibleSignalTimer();
                }
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

    function _setupAudioErrorHandlers( ) {
        // Add error handlers to all audio elements
        const audioElements = document.querySelectorAll('audio[id^="hi-audio-signal-"]');
        audioElements.forEach(function(elem) {
            elem.addEventListener('error', function(e) {
                const signalName = elem.id.replace('hi-audio-signal-', '');
                console.error( `Audio loading error for ${signalName}: ${e.target.error ? e.target.error.message : 'Unknown error'}` );
            });
            
            elem.addEventListener('loadstart', function(e) {
                if ( Hi.DEBUG ) { 
                    const signalName = elem.id.replace('hi-audio-signal-', '');
                    console.log( `Loading audio for ${signalName}` ); 
                }
            });
            
            elem.addEventListener('canplaythrough', function(e) {
                if ( Hi.DEBUG ) { 
                    const signalName = elem.id.replace('hi-audio-signal-', '');
                    console.log( `Audio ready for ${signalName}` ); 
                }
            });
        });
    }

    function _showPermissionGuidanceIfNeeded() {
        // Only show guidance once per browser/user
        if (Hi.settings.hasShownPermissionGuidance()) {
            return;
        }
        
        // Mark as shown to prevent future displays
        Hi.settings.markPermissionGuidanceShown();
        
        // Show the server-rendered notification element
        _showPermissionGuidanceNotification();
    }
    
    function _showPermissionGuidanceNotification() {
        // Show the pre-rendered notification element
        $(Hi.AUDIO_PERMISSION_GUIDANCE_SELECTOR).show();
        
        // Auto-dismiss after 8 seconds
        setTimeout(function() {
            $(Hi.AUDIO_PERMISSION_GUIDANCE_SELECTOR).fadeOut(500);
        }, 8000);
    }

    /*
      AUDIO PERMISSION HANDLING
      
      - Modern browser autoplay policy detection and management
      - Dual-state system: baseline (no user interaction) vs current state
    */
    
    const AudioPermissionState = {
        GRANTED: 'granted',
        BLOCKED: 'blocked', 
        UNKNOWN: 'unknown'
    };
    
    const FirefoxAutoplayPolicy = {
        ALLOWED: 'allowed',
        ALLOWED_MUTED: 'allowed-muted', 
        DISALLOWED: 'disallowed'
    };
    
    const AudioButtonState = {
        ENABLED: 'enabled',
        DISABLED: 'disabled',
        BLOCKED: 'blocked'
    };
    
    function _getAudioPermissionState() {
        if (Hi.DEBUG) { console.log('_getAudioPermissionState() called'); }
        
        // Method 1: Firefox getAutoplayPolicy API
        if (typeof navigator.getAutoplayPolicy === 'function') {
            const policy = navigator.getAutoplayPolicy('mediaelement');
            if (Hi.DEBUG) { console.log('Using navigator.getAutoplayPolicy, result:', policy); }
            
            // Firefox autoplay policy values for BACKGROUND ALERTS:
            // "allowed" = Background alerts can play audio automatically
            // "allowed-muted" = Background alerts blocked (can only play muted audio)
            // "disallowed" = Background alerts completely blocked
            if (policy === FirefoxAutoplayPolicy.ALLOWED) {
                if (Hi.DEBUG) { console.log('Firefox: Background alert audio allowed'); }
                return AudioPermissionState.GRANTED;
            } else {
                if (Hi.DEBUG) { console.log('Firefox: Background alert audio blocked'); }
                return AudioPermissionState.BLOCKED;
            }
        }
        
        // Method 2: Fallback for Chrome/Safari/others
        // Test background alert audio capability (autoplay without user activation)
        if (Hi.DEBUG) { console.log('Testing background alert audio capability...'); }
        const testAudio = document.createElement('audio');
        testAudio.muted = false; 
        testAudio.volume = 0.001; // Nearly silent but not muted - tests real autoplay
        testAudio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+D2w3UlBSuBzvLZiTYIF2ez7eeZVQwKT6zj9r5uHwU8k9n2vpg8Cwi';
        
        // Test autoplay without user activation (same context as background alerts)
        const playPromise = testAudio.play();
        if (playPromise !== undefined) {
            return playPromise.then(() => {
                testAudio.pause();
                if (Hi.DEBUG) { console.log('Background alert audio test succeeded - GRANTED'); }
                return AudioPermissionState.GRANTED;
            }).catch((error) => {
                if (Hi.DEBUG) { console.log('Background alert audio test failed:', error.name); }
                // Handle different browser error types
                if (error.name === 'NotAllowedError' || error.name === 'AbortError') {
                    if (Hi.DEBUG) { console.log('Background alert audio blocked - BLOCKED'); }
                    return AudioPermissionState.BLOCKED;
                }
                if (Hi.DEBUG) { console.log('Unknown autoplay error - UNKNOWN'); }
                return AudioPermissionState.UNKNOWN;
            });
        }
        
        // Very old browsers without Promise support
        if (Hi.DEBUG) { console.log('No Promise support - assuming UNKNOWN'); }
        return AudioPermissionState.UNKNOWN;
    }
    
    async function _requestAudioPermission() {
        try {
            if (Hi.DEBUG) { console.log('Attempting audio permission request via user activation...'); }
            
            // Check current autoplay state before user activation
            const policyBefore = typeof navigator.getAutoplayPolicy === 'function' ? 
                navigator.getAutoplayPolicy('mediaelement') : 'API not available';
            if (Hi.DEBUG) { console.log('Policy before user activation:', policyBefore); }
            
            // Try to play audible test audio with user activation
            const testAudio = document.createElement('audio');
            testAudio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+D2w3UlBSuBzvLZiTYIF2ez7eeZVQwKT6zj9r5uHwU8k9n2vpg8Cwi';
            testAudio.volume = 0.01; 
            testAudio.muted = false;
            
            const playPromise = testAudio.play();
            if (playPromise !== undefined) {
                try {
                    await playPromise;
                    testAudio.pause();
                    if (Hi.DEBUG) { console.log('User activation audio succeeded'); }
                    
                    // Check if Firefox policy changed after user interaction
                    if (typeof navigator.getAutoplayPolicy === 'function') {
                        const policyAfter = navigator.getAutoplayPolicy('mediaelement');
                        if (Hi.DEBUG) { console.log('Policy after user activation:', policyAfter); }
                        
                        if (policyAfter === FirefoxAutoplayPolicy.ALLOWED) {
                            if (Hi.DEBUG) { console.log('Firefox: User activation granted full autoplay permission'); }
                            return AudioPermissionState.GRANTED;
                        } else {
                            if (Hi.DEBUG) { console.log('Firefox: User activation succeeded but autoplay still restricted'); }
                            if (Hi.DEBUG) { console.log('This means audio works with user interaction but not automatically'); }
                            // In this case, we consider permission "granted" for user-activated audio
                            // even though autoplay remains blocked
                            return AudioPermissionState.GRANTED;
                        }
                    } else {
                        // Chrome/Safari: If user activation succeeded, permission is granted
                        if (Hi.DEBUG) { console.log('Chrome/Safari: User activation succeeded - permission granted'); }
                        return AudioPermissionState.GRANTED;
                    }
                } catch (playError) {
                    if (Hi.DEBUG) { console.log('User activation audio failed:', playError.name); }
                    if (playError.name === 'NotAllowedError' || playError.name === 'AbortError') {
                        return AudioPermissionState.BLOCKED;
                    }
                    throw playError;
                }
            }
            return AudioPermissionState.UNKNOWN;
        } catch (error) {
            if (Hi.DEBUG) { console.log('Permission request error:', error.name); }
            if (error.name === 'NotAllowedError' || error.name === 'AbortError') {
                return AudioPermissionState.BLOCKED;
            }
            throw error;
        }
    }

    /*
      AUDIO CONTROL UI MANAGEMENT
      
      - Dual-state audio permission system for button display
      - Baseline monitoring and user interaction handling
    */
    
    // Dual-state audio permission system variables
    const BASELINE_STATE_MONITOR_INTERVAL_MS = 15 * 1000;

    let baselineAudioState = null;  // State immediately after page load (no user interaction)
    let currentAudioState = null;   // State right now (may include user interaction effects)
    let baselineRecheckTimer = null;

    function hasBaselineStateChanged() {
        return currentAudioState !== null && currentAudioState !== baselineAudioState;
    }

    async function _setInitialBaselineState() {
        if (Hi.DEBUG) { console.log('[AUDIO] Setting initial baseline audio state (clean page load)'); }
        
        try {
            const state = await _getAudioPermissionState();
            baselineAudioState = state;
            currentAudioState = state;  // At page load, current state equals baseline state
            
            if (Hi.DEBUG) { console.log(`Initial baseline and current audio state: ${baselineAudioState}`); }
            
            // Update button display based on current state
            await _updateAudioButtonState();
            
            return baselineAudioState;
        } catch (error) {
            if (Hi.DEBUG) { console.error('Error setting initial baseline audio state:', error); }
            return null;
        }
    }
    
    async function _checkForBaselineStateChange() {
        if (hasBaselineStateChanged()) {
            // Already detected a change, no need to keep checking
            return;
        }
        
        if (Hi.DEBUG) { console.log('🔍 Checking for baseline audio state changes'); }
        
        try {
            const state = await _getAudioPermissionState();
            currentAudioState = state;
            
            if (hasBaselineStateChanged()) {
                if (Hi.DEBUG) { console.log(`[AUDIO] Baseline state changed: ${baselineAudioState} → ${currentAudioState}`); }
                
                // Update button display
                await _updateAudioButtonState();
                
                // Stop monitoring since we detected a change
                if (baselineRecheckTimer) {
                    if (Hi.DEBUG) { console.log('🛑 Stopping baseline monitoring - change detected'); }
                    clearInterval(baselineRecheckTimer);
                    baselineRecheckTimer = null;
                }
            } else {
                if (Hi.DEBUG) { console.log(`Baseline state unchanged: ${baselineAudioState}`); }
            }
        } catch (error) {
            if (Hi.DEBUG) { console.error('Error checking for baseline state change:', error); }
        }
    }

    async function _checkCurrentAudioState() {
        if (Hi.DEBUG) { console.log('🔍 Checking current audio state'); }
        
        try {
            const state = await _getAudioPermissionState();
            currentAudioState = state;
            
            if (Hi.DEBUG) { console.log(`Current audio state: ${currentAudioState}`); }
            
            return currentAudioState;
        } catch (error) {
            if (Hi.DEBUG) { console.error('Error checking current audio state:', error); }
            return null;
        }
    }


    async function _startBaselineMonitoring() {
        if (Hi.DEBUG) { console.log('[AUDIO] Starting baseline audio monitoring system'); }
        
        // Set initial baseline immediately on page load (cleanest state)
        await _setInitialBaselineState();
        
        // Only start baseline monitoring if baseline state is blocked
        if (baselineAudioState === AudioPermissionState.BLOCKED) {
            if (Hi.DEBUG) { console.log('[AUDIO] Starting baseline state monitoring (baseline is blocked)'); }
            baselineRecheckTimer = setInterval(async () => {
                await _checkForBaselineStateChange();
            }, BASELINE_STATE_MONITOR_INTERVAL_MS );
        } else {
            if (Hi.DEBUG) { console.log('[AUDIO] Baseline state is allowed - no monitoring needed'); }
        }
    }

    async function _updateAudioButtonState() {
        // Hide all buttons first
        $('#hi-audio-state-enabled').hide();
        $('#hi-audio-state-disabled').hide(); 
        $('#hi-audio-state-blocked').hide();
        
        try {
            // Use current state for button display (fallback to fresh check if needed)
            const permissionState = currentAudioState || await _getAudioPermissionState();
            
            // Priority order: Disabled > Blocked > Enabled
            if (!Hi.settings.isAudioEnabled()) {
                // User has explicitly disabled audio - show disabled (takes precedence)
                $('#hi-audio-state-disabled').show();
            } else if (permissionState === AudioPermissionState.BLOCKED) {
                // User wants audio but permissions are blocked - show blocked
                $('#hi-audio-state-blocked').show();
            } else {
                // User wants audio and permissions are OK - show enabled
                $('#hi-audio-state-enabled').show();
            }
            
            if (Hi.DEBUG) { 
                const changeStatus = hasBaselineStateChanged() ? 'changed' : 'unchanged';
                const userSetting = Hi.settings.isAudioEnabled() ? AudioButtonState.ENABLED : AudioButtonState.DISABLED;
                let buttonState;
                if (!Hi.settings.isAudioEnabled()) {
                    buttonState = AudioButtonState.DISABLED;
                } else if (permissionState === AudioPermissionState.BLOCKED) {
                    buttonState = AudioButtonState.BLOCKED;
                } else {
                    buttonState = AudioButtonState.ENABLED;
                }
                if ( Hi.DEBUG ) { console.log(`Button showing: ${buttonState} (permission: ${permissionState}, user: ${userSetting}, baseline: ${baselineAudioState}, current: ${currentAudioState}, status: ${changeStatus})`); } 
            }
            
        } catch (error) {
            if (Hi.DEBUG) { console.error('Error updating audio button state:', error); }
            // Fallback - show based on settings only (assume permissions are OK)
            if (Hi.settings.isAudioEnabled()) {
                $('#hi-audio-state-enabled').show();
            } else {
                $('#hi-audio-state-disabled').show();
            }
        }
    }

    async function _handleAudioButtonClick() {
        try {
            if (Hi.DEBUG) { console.log('🔘 Audio button clicked'); }
            if (Hi.DEBUG) { console.log(`Current states - baseline: ${baselineAudioState}, current: ${currentAudioState}, settings enabled: ${Hi.settings.isAudioEnabled()}`); }
            
            // Check if we should show guidance dialog
            if (baselineAudioState === AudioPermissionState.BLOCKED && Hi.settings.isAudioEnabled()) {
                if (Hi.DEBUG) { console.log('📋 Showing guidance dialog (baseline blocked + audio enabled)'); }
                await _showAudioPermissionGuidanceDialog();
            } else {
                if (Hi.DEBUG) { console.log('[AUDIO] No guidance needed - normal button toggle'); }
                // Normal case: just toggle audio setting and update button
                if (Hi.settings.isAudioEnabled()) {
                    if (Hi.DEBUG) { console.log('🔇 Disabling audio'); }
                    Hi.settings.disableAudio();
                } else {
                    if (Hi.DEBUG) { console.log('🔊 Enabling audio'); }
                    Hi.settings.enableAudio();
                }
                await _updateAudioButtonState();
            }
        } catch (error) {
            if (Hi.DEBUG) { console.error('[AUDIO ERROR] Error handling audio button click:', error); }
        }
    }
    
    async function _showAudioPermissionGuidanceDialog() {
        try {
            if (Hi.DEBUG) { console.log('[AUDIO] Fetching and showing audio permission guidance dialog...'); }
            
            // Use antinode's direct API instead of triggering events
            if (typeof window.AN !== 'undefined') {
                if (Hi.DEBUG) { console.log('📡 Using antinode AN.get() to fetch modal content'); }
                window.AN.get('/audio/permission-guidance');
            } else {
                if (Hi.DEBUG) { console.log('[AUDIO WARNING] Antinode not available, using fallback approach'); }
                // Fallback: manual AJAX call
                $.get('/audio/permission-guidance')
                 .done(function(html) {
                     if (Hi.DEBUG) { console.log('[AUDIO] Got guidance HTML, creating modal'); }
                     // Create modal manually
                     let modalId = 'audio-guidance-modal-' + Date.now();
                     let modalHtml = `<div id="${modalId}" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">${html}</div>`;
                     $('body').append(modalHtml);
                     $(`#${modalId}`).modal('show');
                 })
                 .fail(function(xhr, status, error) {
                     if (Hi.DEBUG) { console.error('[AUDIO ERROR] Failed to fetch guidance dialog:', error); }
                     alert('Audio is blocked by your browser. Please check your browser\'s autoplay settings.');
                 });
            }
            
            if (Hi.DEBUG) { console.log('🚀 Audio guidance dialog request initiated'); }
        } catch (error) {
            if (Hi.DEBUG) { console.error('[AUDIO ERROR] Error showing audio guidance dialog:', error); }
            // Fallback: show simple alert
            alert('Audio is blocked by your browser. Please check your browser\'s autoplay settings.');
        }
    }

    /*
      DIAGNOSTIC BACKGROUND AUDIO TESTING
      
      - Plays sound every 10 seconds to test autoplay capability
      - Useful for verifying baseline state detection
    */

    // Moule level tracing (w/overall DEBUG safety check)
    const TRACE_AUDIO = false && window.Hi?.Config?.DEBUG;
    
    let diagnosticAudioTimer = null;
    let diagnosticCounter = 0;

    function _startDiagnosticAudio() {
        if ( ! TRACE_AUDIO ) return;
        
        if (Hi.DEBUG) { console.log('🔊 Starting diagnostic background audio (every 10 seconds)'); }
        
        diagnosticAudioTimer = setInterval(() => {
            diagnosticCounter++;
            
            if (Hi.DEBUG) { console.log(`[AUDIO] Diagnostic background audio #${diagnosticCounter}`); }
            
            try {
                // Use the same method as real weather alerts (no user activation)
                _startAudibleSignal('ConsoleInfo');
                if (Hi.DEBUG) { console.log(`[AUDIO] Diagnostic audio #${diagnosticCounter} triggered`); }
            } catch (error) {
                if (Hi.DEBUG) { console.log(`[AUDIO ERROR] Diagnostic audio #${diagnosticCounter} failed:`, error); }
            }
        }, 10000);
    }

    function _stopDiagnosticAudio() {
        if (diagnosticAudioTimer) {
            clearInterval(diagnosticAudioTimer);
            diagnosticAudioTimer = null;
            diagnosticCounter = 0;
            if (Hi.DEBUG) { console.log('🔇 Diagnostic background audio stopped'); }
        }
    }

    // Initialize systems when audio module loads
    window.addEventListener('load', function() {
        _startBaselineMonitoring();
        _startDiagnosticAudio();
    });

})();
