// Video Timeline Scrollbar Management
// Handles scroll behavior for the dual-mode camera interface timeline
// Also manages video stream connections to prevent browser connection limit issues

(function() {
    'use strict';
    
    // Video Connection Management
    const VideoConnectionManager = {
        currentVideo: null,
        previousVideos: [],
        maxCachedVideos: 3, // Keep a few previous videos cached for back navigation
        
        registerVideo: function(videoElement) {
            if (!videoElement) return;
            
            // Clean up old videos before registering new one
            this.cleanupOldVideos();
            
            // Store reference to current video
            this.currentVideo = videoElement;
            
            // Add error handling and load event listeners
            videoElement.addEventListener('error', this.handleVideoError.bind(this));
            videoElement.addEventListener('loadstart', this.handleVideoLoadStart.bind(this));
        },
        
        cleanupOldVideos: function() {
            // If we have a current video, move it to the previous videos cache
            if (this.currentVideo && this.currentVideo.src) {
                this.previousVideos.unshift(this.currentVideo);
                
                // Keep only the most recent N videos cached
                if (this.previousVideos.length > this.maxCachedVideos) {
                    const videosToCleanup = this.previousVideos.splice(this.maxCachedVideos);
                    videosToCleanup.forEach(video => this.forceCloseVideo(video));
                }
            }
        },
        
        forceCloseVideo: function(videoElement) {
            if (!videoElement || !videoElement.src) return;
            
            try {
                // Create a 1x1 pixel transparent GIF data URL to replace the stream
                const transparentGif = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
                
                // Replace the streaming URL with the data URL to close the connection
                videoElement.src = transparentGif;
                
                // Also set srcset if present
                if (videoElement.srcset) {
                    videoElement.srcset = '';
                }
                
                console.debug('Video connection closed:', videoElement.getAttribute('data-event-id') || 'unknown');
            } catch (e) {
                console.warn('Error closing video connection:', e);
            }
        },
        
        handleVideoError: function(event) {
            const video = event.target;
            console.warn('Video error for event:', video.getAttribute('data-event-id'), event);
            
            // If we've hit connection limits, try to free up connections
            if (this.previousVideos.length > 0) {
                console.info('Video error detected, cleaning up old connections...');
                const oldVideo = this.previousVideos.pop();
                this.forceCloseVideo(oldVideo);
                
                // Try to reload the current video after a brief delay
                setTimeout(() => {
                    if (video.src && !video.src.startsWith('data:')) {
                        video.load();
                    }
                }, 500);
            }
        },
        
        handleVideoLoadStart: function(event) {
            const video = event.target;
            console.debug('Video loading started for event:', video.getAttribute('data-event-id'));
        },
        
        // Force cleanup all connections (for page unload)
        cleanup: function() {
            if (this.currentVideo) {
                this.forceCloseVideo(this.currentVideo);
            }
            this.previousVideos.forEach(video => this.forceCloseVideo(video));
            this.previousVideos = [];
            this.currentVideo = null;
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
            // Register the new video element with connection manager
            this.registerCurrentVideo();
        },
        
        registerCurrentVideo: function() {
            // Find the main video element in the video detail container
            const videoElement = document.querySelector('.video-container img');
            if (videoElement && videoElement.src && !videoElement.src.startsWith('data:')) {
                // Set event ID for debugging if available
                const eventId = this.extractEventIdFromUrl(videoElement.src);
                if (eventId) {
                    videoElement.setAttribute('data-event-id', eventId);
                }
                
                VideoConnectionManager.registerVideo(videoElement);
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
            VideoTimelineScrollManager.registerCurrentVideo();
        });
    } else {
        VideoTimelineScrollManager.init();
        VideoTimelineScrollManager.registerCurrentVideo();
    }
    
    // Hook into antinode.js updates
    if (typeof addAfterAsyncRenderFunction === 'function') {
        addAfterAsyncRenderFunction(() => VideoTimelineScrollManager.handleAsyncUpdate());
    } else {
        const original = window.handlePostAsyncUpdate;
        window.handlePostAsyncUpdate = function() {
            if (original) original();
            VideoTimelineScrollManager.handleAsyncUpdate();
        };
    }
    
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