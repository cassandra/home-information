// Video Timeline Scrollbar Management
// Handles scroll behavior for the dual-mode camera interface timeline

(function() {
    'use strict';
    
    // Video Timeline Scrollbar Management
    const VideoTimelineScrollManager = {
        init: function() {
            this.timeline = document.getElementById('event-timeline');
            if (!this.timeline) return;
            
            // Handle initial page loads - scroll to active item if needed
            this.handleInitialLoad();
            
            // Set up button navigation handlers
            this.setupButtonHandlers();
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
        
        setupButtonHandlers: function() {
            // Add custom handlers for navigation buttons only
            const buttons = document.querySelectorAll('.navigation-buttons a');
            buttons.forEach(button => {
                button.addEventListener('click', () => {
                    // Mark that we're using button navigation
                    sessionStorage.setItem('videoTimelineButtonNav', 'true');
                });
            });
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
            // Check if this was button navigation
            const buttonNav = sessionStorage.getItem('videoTimelineButtonNav');
            if (buttonNav) {
                sessionStorage.removeItem('videoTimelineButtonNav');
                
                // Wait for DOM to settle, then scroll to active item
                setTimeout(() => {
                    const activeItem = this.timeline?.querySelector('.timeline-item.active');
                    if (activeItem) {
                        this.scrollToItem(activeItem, 'button');
                    }
                }, 100);
            }
            
            // Re-setup button handlers for new content
            this.setupButtonHandlers();
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => VideoTimelineScrollManager.init());
    } else {
        VideoTimelineScrollManager.init();
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
    
    // Expose for potential external use
    window.VideoTimelineScrollManager = VideoTimelineScrollManager;
})();