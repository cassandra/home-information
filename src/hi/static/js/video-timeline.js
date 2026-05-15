// Video Timeline Scrollbar Management
// Handles scroll behavior for the dual-mode camera interface timeline
// Also manages video stream connections to prevent browser connection limit issues

(function() {
    'use strict';

    const TRANSPARENT_GIF_SRC =
        'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

    // The connection manager treats both markers as the same kind of
    // long-lived MJPEG fetch — both need explicit cleanup on DOM
    // removal so browser per-host connection slots are released. The
    // markers themselves are disjoint by content type:
    //   - ``data-video-stream``    : continuous live MJPEG (camera).
    //   - ``data-video-recording`` : finite recorded MJPEG (event playback).
    // The replay click handler at the bottom of this file applies
    // only to the recording case.
    const LONG_LIVED_VIDEO_SELECTOR =
        'img[data-video-stream], img[data-video-recording]';

    // Tracks every long-lived video connection currently attached to
    // the document.
    //
    // Responsibilities split with antinode:
    //   - Antinode fires ``beforeAsyncRender($target)`` immediately
    //     before replacing a subtree. We register a callback that
    //     force-closes any tracked streams within the outgoing
    //     subtree by swapping ``src`` to a 1x1 transparent GIF. This
    //     terminates the fetch before the browser orphans the
    //     element.
    //   - On each ``afterAsyncRender`` / ``afterModalRender``, we
    //     reconcile: drop entries for elements no longer in the DOM,
    //     register any newly-attached marked elements.
    //   - On page unload we force-close everything.
    const VideoConnectionManager = {

        streams: new Set(),

        register: function( element ) {
            if ( ! element ) return;
            if ( ! element.src || element.src.startsWith('data:') ) return;
            if ( this.streams.has( element )) return;
            this.streams.add( element );
            element.addEventListener( 'error', () => this._handleError( element ));
        },

        forceClose: function( element ) {
            if ( ! element ) return;
            try {
                if ( element.src && ! element.src.startsWith('data:') ) {
                    element.src = TRANSPARENT_GIF_SRC;
                }
                if ( element.srcset ) {
                    element.srcset = '';
                }
            } catch ( e ) {
                console.warn( 'Error closing stream:', e );
            }
            this.streams.delete( element );
        },

        // Walk the outgoing subtree and force-close every marked
        // element within it. Called by antinode's beforeAsyncRender
        // hook before content is replaced.
        closeWithin: function( $scope ) {
            if ( ! $scope || ! $scope.find ) return;
            const manager = this;
            $scope.find( LONG_LIVED_VIDEO_SELECTOR ).each(function() {
                manager.forceClose( this );
            });
        },

        // Re-derive the tracked set from the live DOM. Drops removed
        // elements, registers newly-attached ones.
        reconcile: function() {
            for ( const element of Array.from( this.streams )) {
                if ( ! document.contains( element )) {
                    this.streams.delete( element );
                }
            }
            document.querySelectorAll( LONG_LIVED_VIDEO_SELECTOR ).forEach(
                (el) => this.register( el )
            );
        },

        cleanup: function() {
            for ( const element of Array.from( this.streams )) {
                this.forceClose( element );
            }
        },

        _handleError: function( element ) {
            console.warn( 'Video stream error:', element.src );
        }
    };

    // Video Timeline Scrollbar Management
    const VideoTimelineScrollManager = {
        init: function() {
            this.timeline = document.getElementById('event-timeline');
            if (!this.timeline) return;

            // Handle initial page loads - scroll to active item if needed
            this.handleInitialLoad();

        },

        handleInitialLoad: function() {
            const activeItem = this.timeline.querySelector('.timeline-item.active');
            if (!activeItem) return;

            // Check if coming from live stream
            const fromLive = sessionStorage.getItem('navigatingFromLiveStream');
            if (fromLive) {
                sessionStorage.removeItem('navigatingFromLiveStream');
                // Force scroll to active item - should start at top (case D)
                setTimeout(() => this.scrollToItem(activeItem, 'from-live'), 50);
            } else if (!window.videoTimelineInitialized) {
                // First time loading - center active item (case A)
                window.videoTimelineInitialized = true;
                setTimeout(() => this.scrollToItem(activeItem, 'initial'), 50);
            }
        },


        scrollToItem: function(item, context) {
            if (!item) return;

            const timeline = this.timeline;
            const timelineRect = timeline.getBoundingClientRect();
            const itemRect = item.getBoundingClientRect();

            const isVisible = (
                itemRect.top >= timelineRect.top &&
                itemRect.bottom <= timelineRect.bottom
            );

            if (context === 'initial') {
                // For initial page loads, center the item (unless already visible)
                if (!isVisible) {
                    const itemTop = item.offsetTop;
                    const timelineHeight = timeline.clientHeight;
                    const itemHeight = item.clientHeight;

                    const targetScroll = itemTop - (timelineHeight / 2) + (itemHeight / 2);

                    timeline.scrollTo({
                        top: Math.max(0, targetScroll),
                        behavior: 'auto'
                    });
                }
            } else if (context === 'from-live') {
                // For "Recent Event" button, scroll to top (case D)
                timeline.scrollTo({
                    top: 0,
                    behavior: 'auto'
                });
            } else {
                // For button navigation, minimal scroll to bring into view
                if (!isVisible) {
                    const itemTop = item.offsetTop;
                    const itemHeight = item.clientHeight;
                    const timelineHeight = timeline.clientHeight;
                    const margin = 20; // Small margin from edge

                    let targetScroll;

                    if (itemRect.top < timelineRect.top) {
                        // Item is above visible area - scroll up to show it near top
                        targetScroll = itemTop - margin;
                    } else {
                        // Item is below visible area - scroll down to show it near bottom
                        targetScroll = itemTop - timelineHeight + itemHeight + margin;
                    }

                    timeline.scrollTo({
                        top: Math.max(0, targetScroll),
                        behavior: 'smooth'
                    });
                }
            }
        },

        handleAsyncUpdate: function() {
            // Tag the current video element with its event id for
            // debug visibility in console logs / DOM inspection. The
            // connection manager handles registration itself via the
            // ``data-video-stream`` / ``data-video-recording`` markers.
            this.tagCurrentVideoWithEventId();
        },

        tagCurrentVideoWithEventId: function() {
            const videoElement = document.querySelector('.video-container img');
            if (videoElement && videoElement.src && !videoElement.src.startsWith('data:')) {
                const eventId = this.extractEventIdFromUrl(videoElement.src);
                if (eventId) {
                    videoElement.setAttribute('data-event-id', eventId);
                }
            }
        },

        extractEventIdFromUrl: function(url) {
            // Extract event ID from ZoneMinder URL pattern: ...&event=12345
            const match = url.match(/[&?]event=(\d+)/);
            return match ? match[1] : null;
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            VideoTimelineScrollManager.init();
            VideoTimelineScrollManager.tagCurrentVideoWithEventId();
            VideoConnectionManager.reconcile();
        });
    } else {
        VideoTimelineScrollManager.init();
        VideoTimelineScrollManager.tagCurrentVideoWithEventId();
        VideoConnectionManager.reconcile();
    }

    // Hook into antinode lifecycle. ``beforeContentRemoval`` runs
    // before any subtree is detached — HTML content swap or modal
    // dismissal — with the outgoing subtree. That's where we close
    // stream connections cleanly. ``afterAsyncRender`` and
    // ``afterModalRender`` run after content is in the DOM — that's
    // where we reconcile our tracked set against the new state.
    function registerHook( hookName, fn ) {
        if ( typeof window.AN === 'object'
             && typeof window.AN[ hookName ] === 'function' ) {
            window.AN[ hookName ]( fn );
        }
    }
    registerHook( 'addBeforeContentRemovalFunction', ($subtree) => {
        VideoConnectionManager.closeWithin( $subtree );
    });
    registerHook( 'addAfterAsyncRenderFunction', () => {
        VideoTimelineScrollManager.handleAsyncUpdate();
        VideoConnectionManager.reconcile();
    });
    registerHook( 'addAfterModalRenderFunction', () => {
        VideoConnectionManager.reconcile();
    });

    // Cleanup on page unload to free connections
    window.addEventListener('beforeunload', () => {
        VideoConnectionManager.cleanup();
    });

    // Also cleanup on navigation away from video pages
    window.addEventListener('pagehide', () => {
        VideoConnectionManager.cleanup();
    });

    // Replay-from-start for finite recordings. Templates wrap each
    // ``[data-video-recording]`` <img> in a ``.hi-video-recording``
    // container that also holds a ``.hi-video-recording-replay``
    // button. Delegated on body so async-loaded fragments work
    // without an init pass.
    //
    // Mechanism: append a fresh ``_replay`` query parameter to the
    // cached original URL on each click. The browser sees a new URL,
    // abandons the previous fetch, and starts a new one. ZoneMinder
    // serves the recording from the start on each request
    // (``replay=single``). Avoids ever blanking the ``src`` —
    // some templates carry inline ``onerror`` handlers that fire
    // on empty src and replace the <img> with an error message,
    // which the empty-src + reset technique would trigger.
    function videoRecordingReplayBuster( baseUrl ) {
        const sep = baseUrl.includes('?') ? '&' : '?';
        return baseUrl + sep + '_replay=' + Date.now();
    }
    jQuery(function($) {
        $( 'body' ).on( 'click', '.hi-video-recording-replay', function( ev ) {
            ev.preventDefault();
            ev.stopPropagation();
            const wrapper = this.closest( '.hi-video-recording' );
            const img = wrapper && wrapper.querySelector( 'img[data-video-recording]' );
            if ( ! img ) return;
            // Cache the original URL on first click. Subsequent
            // clicks always rebuild from this cached base so the
            // ``_replay`` parameter doesn't stack.
            if ( ! img.dataset.videoRecordingSrc ) {
                img.dataset.videoRecordingSrc = img.src;
            }
            const baseUrl = img.dataset.videoRecordingSrc;
            if ( ! baseUrl || baseUrl.startsWith('data:') ) return;
            img.src = videoRecordingReplayBuster( baseUrl );
        });
    });


    // Expose for potential external use and debugging
    window.VideoTimelineScrollManager = VideoTimelineScrollManager;
    window.VideoConnectionManager = VideoConnectionManager;
})();
