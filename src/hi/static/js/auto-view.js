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
            // Note: excludes mousemove for performance reasons
            const events = ['mousedown', 'keydown', 'touchstart', 'click'];
            
            // Throttle interaction recording to prevent excessive calls
            const throttledRecordInteraction = this.throttle(() => {
                this.recordInteraction();
            }, 100); // Max once per 100ms
            
            events.forEach(event => {
                // Use passive listeners where possible for better performance
                const options = this.isPassiveEventSupported() && 
                              (event === 'touchstart') ? { passive: true } : false;
                              
                document.addEventListener(event, throttledRecordInteraction, options);
            });
        },

        recordInteraction: function() {
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
            
            // Create visual indicator using CSS classes
            const indicator = $(`
                <div id="auto-view-indicator" class="auto-view-indicator">
                    Auto-switched view: ${reason}
                </div>
            `);
            
            $('body').prepend(indicator);
        },

        hideTransientViewIndicator: function() {
            $('#auto-view-indicator').remove();
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