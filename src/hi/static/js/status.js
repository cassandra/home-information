(function() {
    window.Hi = window.Hi || {};

    const HiStatus = {
        init: function() {
            startServerPolling();
        },
    };
    
    window.Hi.status = HiStatus;

    window.addEventListener('load', function() {
        HiStatus.init();
    });

    /*
      POLLING

      - Periodic polling of server to get status and alerts.
    */

    const TRACE = false;
    
    const ServerPollingWatchdogType = 'serverPolling';
    const ServerPollingStartDelayMs = 1000;
    const ServerPollingIntervalMs = 3 * 1000;
    const PollingErrorNotifyTimeMs = 60 * 1000;
    const ServerErrorMessageSelector = '#hi-server-error-msg';
    const ServerPollingUrl = '/api/status';
    const ServerStartTimestampAttr = 'startTimestamp';
    const ServerTimestampAttr = 'timestamp';
    const LastServerTimestampAttr = 'lastTimestamp';
    const CssClassUpdateMapAttr = 'cssClassUpdateMap';
    const IdReplaceUpdateMapAttr = 'idReplaceUpdateMap';
    const IdReplaceHashMapAttr = 'idReplaceHashMap';
    const TransientViewSuggestionAttr = 'transientViewSuggestion';
    const TransientViewUrlAttr = 'url';
    const TransientViewDurationSecondsAttr = 'durationSeconds';
    const TransientViewPriorityAttr = 'priority';
    const TransientViewTriggerReasonAttr = 'triggerReason';

    const AlertStatusDataAttr = 'alertData';
    const AlertBannerContainerSelector = '#hi-alert-banner-container';
    const AlertBannerContentSelector = '#hi-alert-banner-content';
    const MaxAudioSignalNameAttr = 'maxAudioSignalName';
    const NewAudioSignalNameAttr = 'newAudioSignalName';
    const AlarmMessageHtmlAttr = 'alarmMessageHtml';
    
    let gServerPollingTimer = null;
    let gLastServerPollSuccessTime = (new Date()).getTime();
    let gIsServerErrorShowing = false;
    let gLastStartServerDate = null;
    let gLastServerDate = null;
    
    function startServerPolling() {
        Hi.watchdog.add( ServerPollingWatchdogType, 
                         fetchServerResponse,
                         ServerPollingIntervalMs );
        gServerPollingTimer = setTimeout( fetchServerResponse, ServerPollingStartDelayMs );
    }

    function setServerPollingTimer() {
        gServerPollingTimer = setTimeout( fetchServerResponse, ServerPollingIntervalMs );
    }

    function clearServerPollingTimer() {
        if ( gServerPollingTimer ) {
            clearTimeout( gServerPollingTimer );
            gServerPollingTimer = null;
        }
    }

    function fetchServerResponse() {
        if ( Hi.isEditMode ) {
            if ( Hi.DEBUG && TRACE ) { console.log( "Skipping polling server. Edit mode active." ); }
            Hi.watchdog.ok( ServerPollingWatchdogType );
            clearServerPollingTimer();
            setServerPollingTimer();
            return;
        }

        if ( Hi.DEBUG && TRACE ) { console.log( "Polling server..." ); }
        clearServerPollingTimer();
        
        let url = ServerPollingUrl;
        if ( gLastServerDate ) {
            const lastTimestampString = encodeURIComponent( gLastServerDate.toISOString() );
            url += `?${LastServerTimestampAttr}=${lastTimestampString}`;
        }
        
        $.ajaxSuppressLoader = true;
        $.ajax({
            type: 'GET',
            url: url,

            complete: function (jqXHR, textStatus) {
                $.ajaxSuppressLoader = false;
            },
            success: function( data, status, xhr ) {
                try {
                    Hi.watchdog.ok( ServerPollingWatchdogType );
                    clearServerErrorIfNeeded();
                    gLastServerPollSuccessTime = (new Date()).getTime();
                    handleServerResponse( data, status, xhr );
                    
                } catch (e) {
                    console.error( `Exception parsing server response: ${e} (line=${e.lineNumber})` );
                } finally {
                    setServerPollingTimer();
                }
            },
            error: function (xhr, ajaxOptions, thrownError) {
                try {
                    Hi.watchdog.ok( ServerPollingWatchdogType );
                    console.error( `Server polling error [${xhr.status}] : ${thrownError}` );
                    handlePollingError();

                } catch (e) {
                    console.error( `Exception handling polling error: ${e} (line=${e.lineNumber})` );
                } finally {
                    setServerPollingTimer();
                }
            }
        });
    }

    function handleServerResponse( respObj, textStatus, jqXHR ) {
        if ( Hi.DEBUG && TRACE ) { console.log( "Server response: "+JSON.stringify( respObj)); }

        doServerStartTimeCheck( respObj );
        
        if ( ServerTimestampAttr in respObj ) {
            gLastServerDate = new Date( respObj[ServerTimestampAttr] );
        }
        if ( AlertStatusDataAttr in respObj ) {
            handleAlertStatusData( respObj[AlertStatusDataAttr] );
        }
        if ( IdReplaceUpdateMapAttr in respObj ) {
            handleIdReplacements( respObj[IdReplaceUpdateMapAttr],
                                  respObj[IdReplaceHashMapAttr] );
        }
        if ( CssClassUpdateMapAttr in respObj ) {
            handleCssClassUpdates( respObj[CssClassUpdateMapAttr] );
        }
        if ( TransientViewSuggestionAttr in respObj ) {
            handleTransientViewSuggestion( respObj[TransientViewSuggestionAttr] );
        }
    }

    function doServerStartTimeCheck( respObj ) {
        if ( ServerStartTimestampAttr in respObj ) {
            let startServerDate = new Date( respObj[ServerStartTimestampAttr] );
            if ( gLastStartServerDate ) {
                const timeDifference = Math.abs(startServerDate - gLastStartServerDate.getTime());
                const tolerance = 60 * 1000; // milliseconds
                if (timeDifference > tolerance) {
                    if ( Hi.DEBUG ) {
                        console.log( 'Server restart detected.'
                                     + `Reloading page. ${gLastStartServerDate} -> ${startServerDate}` );
                    }
                    gLastStartServerDate = startServerDate;
                    location.reload(true);
                }
            } else {
                gLastStartServerDate = startServerDate;
            }
        }
    }
    
    function handleAlertStatusData( alertStatusData ) {
        if ( Hi.DEBUG && alertStatusData.length ) {
            console.log('Alert Status Data: ', JSON.stringify(alertStatusData) );
        }

        // Clear audio if no alert data at all
        if ( ! alertStatusData ) {
            Hi.audio.clearAudibleSignal();
            return;
        }
        
        // Clear audio if no active signal (when alerts are acknowledged)
        // Check both existence and value for safety
        if ( ! (MaxAudioSignalNameAttr in alertStatusData) 
             || ! alertStatusData[MaxAudioSignalNameAttr] ) {
            Hi.audio.clearAudibleSignal();
        } else {
            Hi.audio.setActiveSignalName( alertStatusData[MaxAudioSignalNameAttr] );
        }
        
        if (( NewAudioSignalNameAttr in alertStatusData )
            && ( alertStatusData[NewAudioSignalNameAttr] )) {
            Hi.audio.startAudibleSignal( alertStatusData[NewAudioSignalNameAttr] );
        }

        if (( AlarmMessageHtmlAttr in alertStatusData )
            && alertStatusData[AlarmMessageHtmlAttr] ) {
            $(AlertBannerContentSelector).html( alertStatusData[AlarmMessageHtmlAttr] );
            $(AlertBannerContainerSelector).show();
        } else {
            $(AlertBannerContainerSelector).hide();
            $(AlertBannerContentSelector).empty();
        }
    }
    
    function handleIdReplacements( replaceMap, hashMap ) {
        for ( let html_id in replaceMap ) {
            let replacementContent = replaceMap[html_id];
            let contentHash = hashMap[html_id];

            const elem = $(`#${html_id}`);
            if ( $(elem).attr(  'hi-id-replace-hash' ) != contentHash ) {
                $(elem).replaceWith( replacementContent );
                $(`#${html_id}`).attr( 'hi-id-replace-hash', contentHash );
            }
        }
    }
    
    function handleCssClassUpdates( updateMap ) {

        for ( let cssClass in updateMap ) {
            let elements = getElementsByCssClass( cssClass );
            let attrMap = updateMap[cssClass];
            for ( let attrName in attrMap ) {               
                let attrValue = attrMap[attrName];
                elements.each( function() {
                    if (this.hasAttribute(attrName)) {
                        let currentValue = $(this).attr(attrName);
                        if ( attrValue && ( currentValue !== String(attrValue) )) {
                            $(this).attr( attrName, attrValue );
                        }
                    } else {
                        // Special cases:
                        //    - descendent SELECT tag - assume select value is sensor value
                        //    - descendent checkbox - assumes status value 'on' when checked
                        //    - descendent DIV tag with status attr - assume attr and text needs updating
                        //
                        if ( attrName == 'status' ) {
                            $(this).find('select').val( attrValue );
                            
                            $(this).find('input[type="checkbox"]').each( function(index, element) {
                                if ( attrValue == 'on' ) {
                                    $(element).attr( 'checked', 'true' );
                                } else {
                                    $(element).removeAttr( 'checked' );
                                }
                            });
                            
                            $(this).find('div[status]').each( function(index, element) {
                                $(element).attr( attrName, attrValue );
                                $(element).text( attrValue );
                            });
                        }
                    }
                });
            }
        }
    }

    function getElementsByCssClass( cssClass ) {

        let elements = $(`.${cssClass}`);
        return elements;
    }
    
    function handlePollingError() {
        var nowTime = (new Date()).getTime();
        var elapsedMs = nowTime - gLastServerPollSuccessTime;
        if ( Hi.DEBUG ) { console.log( `Polling error elapsedMs=${elapsedMs}` ); }
        
        if ( elapsedMs >= PollingErrorNotifyTimeMs ) {
            notifyServerError();
        }
    }

    function notifyServerError() {
        if ( gIsServerErrorShowing ) {
            return;
        }
        $(ServerErrorMessageSelector).show();
        gIsServerErrorShowing = true;
        Hi.audio.startAudibleSignal( Hi.audio.WARNING_SIGNAL_NAME );
    }

    function clearServerErrorIfNeeded() {
        if ( ! gIsServerErrorShowing ) {
            return;
        }
        $(ServerErrorMessageSelector).hide();
        gIsServerErrorShowing = false;
        Hi.audio.startAudibleSignal( Hi.audio.INFO_SIGNAL_NAME );
    }

    function handleTransientViewSuggestion( suggestionData ) {
        if ( Hi.DEBUG ) { console.log('Transient View Suggestion: ', JSON.stringify(suggestionData) ); }

        if ( ! suggestionData ) {
            return;
        }

        // Build suggestion object using constants
        const suggestion = {
            url: suggestionData[TransientViewUrlAttr],
            durationSeconds: suggestionData[TransientViewDurationSecondsAttr],
            priority: suggestionData[TransientViewPriorityAttr],
            triggerReason: suggestionData[TransientViewTriggerReasonAttr]
        };

        // Delegate to the auto-view module
        if ( Hi.autoView && Hi.autoView.handleTransientViewSuggestion ) {
            Hi.autoView.handleTransientViewSuggestion( suggestion );
        } else {
            console.warn('Auto-view module not available');
        }
    }

})();
