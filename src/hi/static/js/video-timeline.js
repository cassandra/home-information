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
    //   - ``data-video-clip`` : finite recorded MJPEG (event playback).
    // The replay click handler at the bottom of this file applies
    // only to the clip case.
    const LONG_LIVED_VIDEO_SELECTOR =
        'img[data-video-stream], img[data-video-clip]';

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

    // Polls ``[data-video-snapshot]`` <img> elements at their declared
    // ``data-stream-fps`` to synthesize a live feed from a still-image
    // endpoint (HA cameras and any future integration that offers a
    // snapshot URL but no native stream). Pauses while the tab is
    // hidden so bandwidth isn't spent rendering frames the user can't
    // see.
    //
    // Marker contract:
    //   - ``data-video-snapshot``     : presence opts the <img> into polling.
    //   - ``data-stream-fps``         : polling rate (parallel to the Entity
    //                                   model's ``video_snapshot_stream_fps``).
    //
    // Distinct from ``data-video-stream`` / ``data-video-clip``
    // which are continuous MJPEG fetches managed by VideoConnectionManager.
    const SnapshotStreamManager = {

        SELECTOR: 'img[data-video-snapshot]',
        SNAPSHOT_BASE_ATTR: 'snapshotBaseUrl',
        // Defensive cap: faster than 1 fps would risk overlapping
        // preloaders on slow endpoints (a stale older preload could
        // finish after a newer one and swap to an older URL).
        MAX_FPS: 1.0,

        pollers: new Map(),  // element -> intervalId

        register: function( element ) {
            if ( ! element ) return;
            if ( this.pollers.has( element )) return;
            const declared = parseFloat( element.dataset.streamFps );
            if ( ! declared || declared <= 0 ) return;
            const fps = Math.min( declared, this.MAX_FPS );
            const intervalMs = Math.round( 1000 / fps );
            // Strip any server-rendered cache-bust so each poll cycle
            // adds its own; otherwise the URL keeps growing.
            element.dataset[ this.SNAPSHOT_BASE_ATTR ] =
                this._stripCacheBust( element.src );
            const manager = this;
            const intervalId = setInterval(function() {
                if ( document.hidden ) return;
                manager._refresh( element );
            }, intervalMs);
            this.pollers.set( element, intervalId );
        },

        unregister: function( element ) {
            if ( ! element ) return;
            const intervalId = this.pollers.get( element );
            if ( intervalId !== undefined ) {
                clearInterval( intervalId );
            }
            this.pollers.delete( element );
        },

        closeWithin: function( $scope ) {
            if ( ! $scope || ! $scope.find ) return;
            const manager = this;
            $scope.find( this.SELECTOR ).each(function() {
                manager.unregister( this );
            });
        },

        reconcile: function() {
            for ( const element of Array.from( this.pollers.keys() )) {
                if ( ! document.contains( element )) {
                    this.unregister( element );
                }
            }
            document.querySelectorAll( this.SELECTOR ).forEach(
                (el) => this.register( el )
            );
        },

        cleanup: function() {
            for ( const element of Array.from( this.pollers.keys() )) {
                this.unregister( element );
            }
        },

        _refresh: function( element ) {
            const base = element.dataset[ this.SNAPSHOT_BASE_ATTR ] || element.src;
            const sep = base.includes( '?' ) ? '&' : '?';
            const newUrl = base + sep + '_cb=' + Date.now();
            // Preload pattern: fetch into a hidden Image first, swap the
            // visible <img>'s src only after a successful load. Avoids
            // flicker from in-flight fetches that get aborted by the next
            // poll's src change. On preload failure, assign the failing
            // URL to the visible <img> so VideoErrorHandler surfaces the
            // outage; the next successful preload heals the placeholder.
            const preloader = new Image();
            preloader.onload = function() {
                element.src = newUrl;
            };
            preloader.onerror = function() {
                element.src = newUrl;
            };
            preloader.src = newUrl;
        },

        _stripCacheBust: function( url ) {
            try {
                const u = new URL( url, window.location.href );
                u.searchParams.delete( '_cb' );
                return u.toString();
            } catch ( e ) {
                return url;
            }
        }
    };

    // Generic ``error``-event handler for the three video-marker <img>
    // elements (``data-video-stream``, ``data-video-clip``,
    // ``data-video-snapshot``). On load failure, hides the <img> and
    // inserts a sibling placeholder; on a subsequent successful load,
    // hides the placeholder and reveals the <img> again. Self-healing
    // is important for snapshot polling (transient HA blip shouldn't
    // permanently kill the feed) and harmless for the long-lived
    // streams (the placeholder just shows until the user navigates).
    //
    // Coordinates with VideoConnectionManager.forceClose: that path
    // sets ``src`` to a transparent GIF (``data:image/gif;...``).
    // Browsers don't fire ``error`` on a successfully-loaded data
    // URI, but we also explicitly skip ``data:`` URLs as defense.
    const VideoErrorHandler = {

        SELECTOR: 'img[data-video-stream], img[data-video-clip], img[data-video-snapshot]',
        PLACEHOLDER_CLASS: 'video-load-error-placeholder',
        REGISTERED_FLAG: 'videoErrorHandlerRegistered',

        // Heading + subtitle per marker. Mirrors the server-rendered
        // ``.video-placeholder`` markup in entity_video_sensor_history.html
        // for the no-source case, so the failed-to-load and no-data cases
        // look visually identical.
        MESSAGES: {
            'data-video-stream': {
                heading: 'Live View Unavailable',
                subtitle: 'The integration may be offline or the camera unreachable',
            },
            'data-video-clip': {
                heading: 'Video No Longer Available',
                subtitle: 'This clip could not be loaded',
            },
            'data-video-snapshot': {
                heading: 'Snapshot Unavailable',
                subtitle: 'The integration may be offline or unable to provide a snapshot',
            },
        },

        // Reuses the camera icon from the server-rendered placeholder.
        CAMERA_ICON_SVG:
            '<svg width="64" height="64" fill="currentColor" viewBox="0 0 16 16">' +
            '<path d="M10.5 8.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>' +
            '<path d="M2 4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-1.172a2 2 0 0 1-1.414-.586l-.828-.828A2 2 0 0 0 9.172 2H6.828a2 2 0 0 0-1.414.586l-.828.828A2 2 0 0 1 3.172 4H2zm.5 2a.5.5 0 1 1 0-1 .5.5 0 0 1 0 1zm9 2.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0z"/>' +
            '</svg>',

        register: function( element ) {
            if ( ! element ) return;
            if ( element.dataset[ this.REGISTERED_FLAG ] ) return;
            element.dataset[ this.REGISTERED_FLAG ] = '1';
            const handler = this;
            element.addEventListener( 'error', function() {
                handler._handleError( element );
            });
            element.addEventListener( 'load', function() {
                handler._handleLoad( element );
            });
        },

        _handleError: function( element ) {
            if ( element.src && element.src.startsWith( 'data:' )) return;
            element.style.display = 'none';
            const existing = this._findSiblingPlaceholder( element );
            if ( existing ) return;
            const placeholder = this._buildPlaceholder( element );
            element.insertAdjacentElement( 'afterend', placeholder );
        },

        _handleLoad: function( element ) {
            if ( element.src && element.src.startsWith( 'data:' )) return;
            element.style.display = '';
            const existing = this._findSiblingPlaceholder( element );
            if ( existing ) existing.remove();
        },

        _findSiblingPlaceholder: function( element ) {
            const next = element.nextElementSibling;
            if ( next && next.classList
                 && next.classList.contains( this.PLACEHOLDER_CLASS )) {
                return next;
            }
            return null;
        },

        _buildPlaceholder: function( element ) {
            const messages = this._messagesFor( element );
            const wrapper = document.createElement( 'div' );
            wrapper.className =
                'video-placeholder d-flex align-items-center justify-content-center '
                + this.PLACEHOLDER_CLASS;
            wrapper.innerHTML =
                '<div class="text-center">'
                + '<div class="video-placeholder-icon mb-3">'
                + this.CAMERA_ICON_SVG
                + '</div>'
                + '<h5 class="mb-2"></h5>'
                + '<small class="text-muted"></small>'
                + '</div>';
            wrapper.querySelector( 'h5' ).textContent = messages.heading;
            wrapper.querySelector( 'small' ).textContent = messages.subtitle;
            return wrapper;
        },

        _messagesFor: function( element ) {
            for ( const marker of Object.keys( this.MESSAGES )) {
                if ( element.hasAttribute( marker )) return this.MESSAGES[ marker ];
            }
            return { heading: 'Image Unavailable', subtitle: '' };
        },

        reconcile: function() {
            const handler = this;
            document.querySelectorAll( this.SELECTOR ).forEach(
                (el) => handler.register( el )
            );
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
            // ``data-video-stream`` / ``data-video-clip`` markers.
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
    function initVideoSubsystems() {
        VideoTimelineScrollManager.init();
        VideoTimelineScrollManager.tagCurrentVideoWithEventId();
        VideoConnectionManager.reconcile();
        SnapshotStreamManager.reconcile();
        VideoErrorHandler.reconcile();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVideoSubsystems);
    } else {
        initVideoSubsystems();
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
        SnapshotStreamManager.closeWithin( $subtree );
    });
    registerHook( 'addAfterAsyncRenderFunction', () => {
        VideoTimelineScrollManager.handleAsyncUpdate();
        VideoConnectionManager.reconcile();
        SnapshotStreamManager.reconcile();
        VideoErrorHandler.reconcile();
    });
    registerHook( 'addAfterModalRenderFunction', () => {
        VideoConnectionManager.reconcile();
        SnapshotStreamManager.reconcile();
        VideoErrorHandler.reconcile();
    });

    // Cleanup on page unload to free connections and stop pollers
    window.addEventListener('beforeunload', () => {
        VideoConnectionManager.cleanup();
        SnapshotStreamManager.cleanup();
    });

    // Also cleanup on navigation away from video pages
    window.addEventListener('pagehide', () => {
        VideoConnectionManager.cleanup();
        SnapshotStreamManager.cleanup();
    });

    // Replay-from-start for finite clips. Templates wrap each
    // ``[data-video-clip]`` <img> in a ``.hi-video-clip``
    // container that also holds a ``.hi-video-clip-replay``
    // button. Delegated on body so async-loaded fragments work
    // without an init pass.
    //
    // Mechanism: append a fresh ``_replay`` query parameter to the
    // cached original URL on each click. The browser sees a new URL,
    // abandons the previous fetch, and starts a new one. ZoneMinder
    // serves the clip from the start on each request
    // (``replay=single``). Avoids blanking the ``src`` — an empty
    // src would fire ``error`` and trigger ``VideoErrorHandler``'s
    // placeholder.
    function videoClipReplayBuster( baseUrl ) {
        const sep = baseUrl.includes('?') ? '&' : '?';
        return baseUrl + sep + '_replay=' + Date.now();
    }
    jQuery(function($) {
        $( 'body' ).on( 'click', '.hi-video-clip-replay', function( ev ) {
            ev.preventDefault();
            ev.stopPropagation();
            const wrapper = this.closest( '.hi-video-clip' );
            if ( ! wrapper ) return;

            // <video> path (native MP4 clip): seek-to-zero +
            // play. The native element has its own seek/playhead so
            // we don't need the cache-bust trick that <img> uses.
            const video = wrapper.querySelector( 'video[data-video-clip]' );
            if ( video ) {
                try { video.currentTime = 0; } catch ( e ) {}
                const playPromise = video.play();
                if ( playPromise && playPromise.catch ) {
                    playPromise.catch( () => {} );
                }
                return;
            }

            // <img> path (multipart MJPEG clip). Cache the
            // original URL on first click; subsequent clicks always
            // rebuild from this cached base so the ``_replay``
            // parameter doesn't stack.
            const img = wrapper.querySelector( 'img[data-video-clip]' );
            if ( ! img ) return;
            if ( ! img.dataset.videoClipSrc ) {
                img.dataset.videoClipSrc = img.src;
            }
            const baseUrl = img.dataset.videoClipSrc;
            if ( ! baseUrl || baseUrl.startsWith('data:') ) return;
            img.src = videoClipReplayBuster( baseUrl );
        });
    });


    // Expose for potential external use and debugging
    window.VideoTimelineScrollManager = VideoTimelineScrollManager;
    window.VideoConnectionManager = VideoConnectionManager;
    window.SnapshotStreamManager = SnapshotStreamManager;
    window.VideoErrorHandler = VideoErrorHandler;
})();
