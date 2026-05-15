// Video Timeline Scrollbar Management
// Handles scroll behavior for the dual-mode camera interface timeline
// Also manages video stream connections to prevent browser connection limit issues

(function() {
    'use strict';

    const TRANSPARENT_GIF_SRC =
        'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

    // Tracks every long-lived video connection currently attached to
    // the document. An <img> opts in by carrying ``data-video-stream``;
    // both live MJPEG streams and event-video playback elements need
    // this because surveillance users typically browse between events
    // faster than playback completes, leaving recorded-video fetches
    // holding browser per-host connection slots if not closed.
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
            $scope.find( 'img[data-video-stream]' ).each(function() {
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
            document.querySelectorAll( 'img[data-video-stream]' ).forEach(
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
            // ``data-video-stream`` marker.
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

    // Hook into antinode lifecycle. ``beforeAsyncRender`` runs before
    // each HTML content swap with the outgoing $target — that's where
    // we close stream connections cleanly. ``afterAsyncRender`` and
    // ``afterModalRender`` run after content is in the DOM — that's
    // where we reconcile our tracked set against the new state.
    function registerHook( hookName, fn ) {
        if ( typeof window.AN === 'object'
             && typeof window.AN[ hookName ] === 'function' ) {
            window.AN[ hookName ]( fn );
        }
    }
    registerHook( 'addBeforeAsyncRenderFunction', ($target) => {
        VideoConnectionManager.closeWithin( $target );
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


    // Expose for potential external use and debugging
    window.VideoTimelineScrollManager = VideoTimelineScrollManager;
    window.VideoConnectionManager = VideoConnectionManager;
})();
