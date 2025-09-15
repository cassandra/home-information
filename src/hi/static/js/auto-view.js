(function() {
    window.Hi = window.Hi || {};

    const AutoView = {
        // Configuration constants
        IDLE_TIMEOUT_SECONDS: 60,

        // State tracking
        lastInteractionTime: Date.now(),
        isTransientView: false,
        revertTimer: null,
        originalContent: null,
        originalUrl: null,
        transientUrls: [],

        init: function() {
            this.attachInteractionListeners();
            if (Hi.DEBUG) {
                console.log('AutoView initialized');
            }
        },

        // User interaction tracking
        attachInteractionListeners: function() {
            // Enhanced event detection for iOS compatibility
            // Includes touch events, scroll events, and iOS-specific gesture events
            const basicEvents = ['mousedown', 'keydown', 'click'];
            const touchEvents = ['touchstart', 'touchend', 'touchmove'];
            const scrollEvents = ['scroll', 'wheel'];
            const gestureEvents = ['gesturestart', 'gesturechange', 'gestureend'];

            // All events to monitor
            const allEvents = [...basicEvents, ...touchEvents, ...scrollEvents, ...gestureEvents];

            // Event-specific throttle delays (ms)
            const throttleDelays = {
                'touchmove': 200,   // Less frequent for performance
                'scroll': 200,      // Less frequent for performance
                'wheel': 200,       // Less frequent for performance
                'gesturechange': 200, // Less frequent for performance
                'default': 100      // Standard throttle for most events
            };

            allEvents.forEach(event => {
                // Get throttle delay for this event type
                const throttleDelay = throttleDelays[event] || throttleDelays.default;

                // Create throttled function for each event type to capture event name
                const throttledRecordInteraction = this.throttle(() => {
                    this.recordInteraction(event);
                }, throttleDelay);

                // Determine passive option based on event type
                const shouldUsePassive = this.isPassiveEventSupported() &&
                    ['touchstart', 'touchmove', 'scroll', 'wheel'].includes(event);
                const options = shouldUsePassive ? { passive: true } : false;

                try {
                    document.addEventListener(event, throttledRecordInteraction, options);
                    // Log successful listener attachment in debug mode
                    if (Hi.DEBUG && ['gesturestart', 'gesturechange', 'gestureend'].includes(event)) {
                        console.log(`AutoView: Added ${event} listener (iOS gesture support)`);
                    }
                } catch (error) {
                    // Some older browsers may not support certain events
                    if (Hi.DEBUG) {
                        console.warn(`AutoView: Failed to add ${event} listener:`, error);
                    }
                }
            });

        },

        recordInteraction: function(eventType = 'unknown') {
            this.lastInteractionTime = Date.now();

            // If we're in a transient view and user interacts, make it permanent
            if (this.isTransientView) {
                this.makeTransientViewPermanent();
            }
        },

        // Helper method to check if passive events are supported
        isPassiveEventSupported: function() {
            if (this._passiveSupported !== undefined) {
                return this._passiveSupported;
            }
            
            this._passiveSupported = false;
            try {
                const options = {
                    get passive() {
                        this._passiveSupported = true;
                        return false;
                    }
                };
                window.addEventListener('test', null, options);
                window.removeEventListener('test', null, options);
            } catch (err) {
                this._passiveSupported = false;
            }
            
            return this._passiveSupported;
        },

        // Throttle function to limit how often a function can be called
        throttle: function(func, delay) {
            let timeoutId;
            let lastExecTime = 0;
            
            return function(...args) {
                const currentTime = Date.now();
                
                if (currentTime - lastExecTime > delay) {
                    func.apply(this, args);
                    lastExecTime = currentTime;
                } else {
                    clearTimeout(timeoutId);
                    timeoutId = setTimeout(() => {
                        func.apply(this, args);
                        lastExecTime = Date.now();
                    }, delay - (currentTime - lastExecTime));
                }
            };
        },

        // ===== AUTO-VIEW DECISION LOGIC =====
        handleTransientViewSuggestion: function(suggestion) {
            if (!this.shouldAutoSwitch(suggestion)) {
                return;
            }
            
            // If already in transient view, switch to new suggestion and reset timer
            if (this.isTransientView) {
                this.clearRevertTimer();
                this.hideTransientViewIndicator();
            }
            
            this.navigateToTransientView(suggestion);
        },

        shouldAutoSwitch: function(suggestion) {
            const idleTime = Date.now() - this.lastInteractionTime;
            const idleTimeSeconds = idleTime / 1000;
            
            if (idleTimeSeconds < this.IDLE_TIMEOUT_SECONDS) {
                if (Hi.DEBUG) {
                    console.log(`User not idle enough: ${idleTimeSeconds}s < ${this.IDLE_TIMEOUT_SECONDS}s required`);
                }
                return false;
            }
            
            return true;
        },

        // ===== VIEW MANAGEMENT =====
        navigateToTransientView: function(suggestion) {
            const url = suggestion.url;
            const durationSeconds = suggestion.durationSeconds;

            if (Hi.DEBUG) {
                console.log(`Auto-switching to: ${url} for ${durationSeconds}s (reason: ${suggestion.triggerReason})`);
            }
            
            // Store current content and URL for potential revert
            if (!this.isTransientView) {
                this.originalContent = $(Hi.MAIN_AREA_SELECTOR).html();
                this.originalUrl = window.location.href;
                this.transientUrls = []; // Reset the list for new transient session
            }
            
            // Track this URL as it will be pushed by antinode.js
            this.transientUrls.push(url);
            
            this.isTransientView = true;
            
            // Load content asynchronously using antinode pattern
            this.loadContentAsync(url);
            
            // Set revert timer
            this.revertTimer = setTimeout(() => {
                this.revertToOriginalView();
            }, durationSeconds * 1000);
            
            // Show visual indicator
            this.showTransientViewIndicator(suggestion.triggerReason);
        },

        loadContentAsync: function(url) {
            // Use the new public API from antinode.js for loading async content
            // This feature requires antinode.js to be loaded
            if (!window.AN || !window.AN.loadAsyncContent) {
                console.error('Auto-view requires antinode.js with loadAsyncContent method');
                return;
            }
            
            window.AN.loadAsyncContent({
                url: url,
                target: Hi.MAIN_AREA_SELECTOR,
                mode: 'insert',  // Replace inner content, not the element itself
                error: (xhr, ajaxOptions, thrownError) => {
                    console.error(`Auto-view content loading error [${xhr.status}]: ${thrownError}`);
                    // Revert on error
                    this.revertToOriginalView();
                }
            });
        },

        revertToOriginalView: function() {
            if (!this.isTransientView || !this.originalContent) {
                return;
            }

            if (Hi.DEBUG) {
                console.log(`Reverting to original view and URL: ${this.originalUrl}`);
            }
            
            // Restore original content directly
            // Note: We can't use AN.loadAsyncContent here since we have HTML content, not a URL
            // We just do direct DOM manipulation since this is reverting to cached content
            const $target = $(Hi.MAIN_AREA_SELECTOR);
            $target.html(this.originalContent);
            
            // Restore original URL using proper history semantics
            // Since antinode.js pushed the transient URL, we should pop it back off the stack
            this.restoreOriginalUrl();
            
            // Note: antinode's handleNewContentAdded is internal and handles autofocus/modals
            // Since we're restoring previous content, those behaviors aren't needed here
            
            this.resetTransientState();
        },

        restoreOriginalUrl: function() {
            if (!this.originalUrl) {
                if (Hi.DEBUG) {
                    console.log('No original URL stored, skipping URL restoration');
                }
                return;
            }
            
            if (Hi.DEBUG) {
                console.log(`Restoring original URL: ${this.originalUrl}, Transient URLs to pop: [${this.transientUrls.join(', ')}]`);
            }
            
            // Pop all transient URLs with sanity checking
            while (this.transientUrls.length > 0) {
                const expectedUrl = this.transientUrls.pop();
                if (!this.popTransientUrlIfMatches(expectedUrl)) {
                    break; // Stop popping and use fallback
                }
            }
            
            // Final verification: ensure we're on the original URL
            const finalUrl = window.location.href;
            if (finalUrl !== this.originalUrl) {
                if (Hi.DEBUG) {
                    console.warn(`Final URL ${finalUrl} doesn't match original ${this.originalUrl}. Using replaceState to enforce invariant.`);
                }
                // Enforce the invariant: original URL must be on top when done
                window.history.replaceState({}, '', this.originalUrl);
            } else {
                if (Hi.DEBUG) {
                    console.log(`Successfully restored original URL: ${finalUrl}`);
                }
            }
            
            // Clear the transient URL list
            this.transientUrls = [];
        },

        makeTransientViewPermanent: function() {
            if (Hi.DEBUG) {
                console.log('Making transient view permanent due to user interaction');
            }
            
            this.resetTransientState();
        },

        // ===== VISUAL INDICATORS =====
        showTransientViewIndicator: function(reason) {
            // Remove any existing indicator
            this.hideTransientViewIndicator();
            
            // Add border/frame effect to main content area
            const $mainContent = $(Hi.MAIN_AREA_SELECTOR);
            $mainContent.addClass('auto-view-active');
            
            // Create corner badge with reason and subtle animation
            const indicator = $(`
                <div id="auto-view-indicator" class="auto-view-corner-badge">
                    <div class="auto-view-badge-icon">↻</div>
                    <div class="auto-view-badge-text">Auto-view: ${this.formatReason(reason)}</div>
                </div>
            `);
            
            // Portal approach: append to body and calculate position
            $('body').append(indicator);
            this.positionCornerBadge();
            
            // Reposition on window resize
            $(window).on('resize.auto-view', () => {
                this.positionCornerBadge();
            });
        },

        hideTransientViewIndicator: function() {
            $('#auto-view-indicator').remove();
            $(Hi.MAIN_AREA_SELECTOR).removeClass('auto-view-active');
            $(window).off('resize.auto-view');
        },
        
        positionCornerBadge: function() {
            const $indicator = $('#auto-view-indicator');
            const $mainContent = $(Hi.MAIN_AREA_SELECTOR);
            
            if ($indicator.length && $mainContent.length) {
                const mainRect = $mainContent[0].getBoundingClientRect();
                
                // Position in bottom-right corner of main content area, flush to boundary
                $indicator.css({
                    position: 'fixed',
                    bottom: $(window).height() - mainRect.bottom,
                    right: $(window).width() - mainRect.right,
                    maxWidth: mainRect.width,
                    zIndex: 9999
                });
            }
        },
        
        formatReason: function(reason) {
            // Convert technical reasons to user-friendly text
            const reasonMap = {
                'motion_alert': 'Motion Detected',
                'security_alert': 'Security Alert',
                'camera_alert': 'Camera Alert',
                'sensor_alert': 'Sensor Alert'
            };
            
            return reasonMap[reason] || reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        },

        // ===== HELPER METHODS =====
        clearRevertTimer: function() {
            if (this.revertTimer) {
                clearTimeout(this.revertTimer);
                this.revertTimer = null;
            }
        },

        resetTransientState: function() {
            this.clearRevertTimer();
            this.isTransientView = false;
            this.hideTransientViewIndicator();
            this.originalContent = null;
            this.originalUrl = null;
            this.transientUrls = [];
        },

        popTransientUrlIfMatches: function(expectedUrl) {
            const currentUrl = window.location.href;
            
            if (currentUrl === expectedUrl) {
                if (Hi.DEBUG) {
                    console.log(`Popping expected transient URL: ${expectedUrl}`);
                }
                try {
                    window.history.back();
                    return true;
                } catch (error) {
                    console.warn(`Failed to pop URL ${expectedUrl}:`, error);
                    return false;
                }
            } else {
                if (Hi.DEBUG) {
                    console.warn(`URL mismatch. Expected: ${expectedUrl}, Current: ${currentUrl}. Stopping history manipulation.`);
                }
                return false;
            }
        }
    };

    window.Hi.autoView = AutoView;

    // Initialize when page loads
    window.addEventListener('load', function() {
        AutoView.init();
    });

})();
