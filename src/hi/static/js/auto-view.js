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
            events.forEach(event => {
                document.addEventListener(event, () => {
                    this.recordInteraction();
                });
            });
        },

        recordInteraction: function() {
            this.lastInteractionTime = Date.now();
            
            // If we're in a transient view and user interacts, make it permanent
            if (this.isTransientView) {
                this.makeTransientViewPermanent();
            }
        },

        // Auto-view decision logic
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

        // View management
        navigateToTransientView: function(suggestion) {
            const url = suggestion.url;
            const durationSeconds = suggestion.durationSeconds;
            
            if (Hi.DEBUG) {
                console.log(`Auto-switching to: ${url} for ${durationSeconds}s (reason: ${suggestion.triggerReason})`);
            }
            
            // Store current content for potential revert
            if (!this.isTransientView) {
                this.originalContent = $(Hi.MAIN_AREA_SELECTOR).html();
            }
            
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
            // Use jQuery AJAX to fetch content and process it with antinode's asyncUpdateData
            $.ajax({
                type: 'GET',
                url: url,
                success: (data, status, xhr) => {
                    const $target = $(Hi.MAIN_AREA_SELECTOR);
                    
                    // Use antinode's asyncUpdateData to handle content insertion properly
                    if (window.asyncUpdateData) {
                        window.asyncUpdateData($target, null, data, xhr);
                    } else {
                        // Fallback: html() replaces content inside target element
                        $target.html(data);
                        // Call handleNewContentAdded to ensure event handlers are attached
                        if (window.handleNewContentAdded) {
                            window.handleNewContentAdded($target);
                        }
                    }
                },
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
                console.log('Reverting to original view');
            }
            
            this.clearRevertTimer();
            this.isTransientView = false;
            
            // Restore original content
            const $target = $(Hi.MAIN_AREA_SELECTOR);
            $target.html(this.originalContent);
            
            // Call handleNewContentAdded to reattach event handlers
            if (window.handleNewContentAdded) {
                window.handleNewContentAdded($target);
            }
            
            this.hideTransientViewIndicator();
            this.originalContent = null;
        },

        makeTransientViewPermanent: function() {
            if (Hi.DEBUG) {
                console.log('Making transient view permanent due to user interaction');
            }
            
            this.clearRevertTimer();
            this.isTransientView = false;
            this.hideTransientViewIndicator();
            this.originalContent = null;
        },

        // Visual indicators
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

        // Helper methods
        clearRevertTimer: function() {
            if (this.revertTimer) {
                clearTimeout(this.revertTimer);
                this.revertTimer = null;
            }
        }
    };

    window.Hi.autoView = AutoView;

    // Initialize when page loads
    window.addEventListener('load', function() {
        AutoView.init();
    });

})();