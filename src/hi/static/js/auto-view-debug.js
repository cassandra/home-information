/**
 * Auto-View Debug Overlay (Isolated)
 *
 * Observer-based debug overlay for auto-view functionality. Completely isolated
 * from production code and only activates when explicitly enabled via Django settings.
 *
 * Architecture:
 * - Uses observer pattern to monitor auto-view without modifying it
 * - Self-initializes when conditions are met
 * - Zero impact when disabled
 * - Follows Django Pipeline and HiClientConfig patterns
 */

(function() {
    'use strict';

    // Early exit if debug overlay not enabled
    if (!window.HiClientConfig?.DEBUG_AUTO_VIEW_OVERLAY) {
        return;
    }

    // Wait for auto-view to be available
    function waitForAutoView(callback, maxAttempts = 50, attempt = 0) {
        if (window.Hi?.autoView) {
            callback();
        } else if (attempt < maxAttempts) {
            setTimeout(() => waitForAutoView(callback, maxAttempts, attempt + 1), 100);
        } else {
            console.warn('AutoViewDebug: Timeout waiting for auto-view module');
        }
    }

    const AutoViewDebug = {
        // Configuration
        UPDATE_INTERVAL_MS: 1000,
        MAX_EVENT_LOG_SIZE: 5,

        // State
        isInitialized: false,
        overlayElement: null,
        updateInterval: null,
        eventLog: [],
        originalMethods: {},

        init: function() {
            if (this.isInitialized) return;

            this.createOverlay();
            this.interceptAutoViewMethods();
            this.startUpdateLoop();
            this.detectPlatform();
            this.isInitialized = true;

            this.logEvent('SYSTEM', 'Debug overlay initialized');

            if (window.Hi.DEBUG) {
                console.log('AutoView Debug Overlay: Initialized');
            }
        },

        createOverlay: function() {
            this.overlayElement = document.createElement('div');
            this.overlayElement.id = 'auto-view-debug-overlay';
            this.overlayElement.innerHTML = this.getOverlayHTML();

            this.applyStyles();
            this.attachEventListeners();

            document.body.appendChild(this.overlayElement);
        },

        getOverlayHTML: function() {
            return `
                <div class="debug-header">
                    <span class="debug-title">Auto-View Debug</span>
                    <div class="debug-controls">
                        <button class="debug-minimize" title="Minimize">−</button>
                        <button class="debug-close" title="Close">×</button>
                    </div>
                </div>
                <div class="debug-content">
                    <div class="debug-row">
                        <span class="debug-label">Status:</span>
                        <span class="debug-value" id="debug-status">Initializing...</span>
                    </div>
                    <div class="debug-row">
                        <span class="debug-label">Idle:</span>
                        <span class="debug-value" id="debug-idle">0.0s</span>
                    </div>
                    <div class="debug-row">
                        <span class="debug-label">Platform:</span>
                        <span class="debug-value" id="debug-platform">Unknown</span>
                    </div>
                    <div class="debug-row">
                        <span class="debug-label">Touch:</span>
                        <span class="debug-value" id="debug-touch">Unknown</span>
                    </div>
                    <div class="debug-row">
                        <span class="debug-label">Events:</span>
                        <div class="debug-events" id="debug-events">No events</div>
                    </div>
                </div>
            `;
        },

        applyStyles: function() {
            let styleElement = document.getElementById('auto-view-debug-styles');
            if (!styleElement) {
                styleElement = document.createElement('style');
                styleElement.id = 'auto-view-debug-styles';
                document.head.appendChild(styleElement);
            }

            styleElement.textContent = `
                #auto-view-debug-overlay {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    width: 280px;
                    background: rgba(0, 0, 0, 0.9);
                    color: #fff;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                    border-radius: 6px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                    z-index: 10000;
                    border: 1px solid #333;
                    user-select: none;
                }

                .debug-header {
                    background: #1a1a1a;
                    padding: 6px 10px;
                    border-bottom: 1px solid #333;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-radius: 6px 6px 0 0;
                }

                .debug-title {
                    font-weight: bold;
                    color: #4a9eff;
                    font-size: 12px;
                }

                .debug-controls {
                    display: flex;
                    gap: 4px;
                }

                .debug-controls button {
                    background: #333;
                    border: none;
                    color: #fff;
                    width: 18px;
                    height: 18px;
                    border-radius: 2px;
                    cursor: pointer;
                    font-size: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .debug-controls button:hover {
                    background: #555;
                }

                .debug-content {
                    padding: 8px 10px;
                }

                .debug-row {
                    margin-bottom: 4px;
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                }

                .debug-label {
                    color: #aaa;
                    min-width: 60px;
                    flex-shrink: 0;
                }

                .debug-value {
                    color: #fff;
                    text-align: right;
                    word-break: break-word;
                    flex-grow: 1;
                }

                .debug-events {
                    color: #fff;
                    text-align: right;
                    font-size: 10px;
                    line-height: 1.3;
                    max-height: 80px;
                    overflow-y: auto;
                    flex-grow: 1;
                }

                .debug-event {
                    margin-bottom: 2px;
                    padding: 2px 4px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 2px;
                }

                .debug-event-time {
                    color: #888;
                    font-size: 9px;
                }

                /* Status colors */
                .status-idle { color: #ff6b6b !important; font-weight: bold; }
                .status-active { color: #51cf66 !important; font-weight: bold; }
                .status-transient { color: #ffd43b !important; font-weight: bold; }

                /* Minimized state */
                #auto-view-debug-overlay.minimized {
                    width: 60px;
                    height: 30px;
                }

                #auto-view-debug-overlay.minimized .debug-content {
                    display: none;
                }

                #auto-view-debug-overlay.minimized .debug-title {
                    font-size: 10px;
                }

                /* Mobile responsive */
                @media (max-width: 768px) {
                    #auto-view-debug-overlay {
                        width: 240px;
                        font-size: 10px;
                        bottom: 10px;
                        left: 10px;
                    }

                    .debug-label {
                        min-width: 50px;
                    }
                }
            `;
        },

        attachEventListeners: function() {
            const minimizeBtn = this.overlayElement.querySelector('.debug-minimize');
            const closeBtn = this.overlayElement.querySelector('.debug-close');
            const header = this.overlayElement.querySelector('.debug-header');

            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', () => this.toggleMinimize());
            }

            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hide());
            }

            if (header) {
                header.addEventListener('dblclick', () => this.toggleMinimize());
            }
        },

        interceptAutoViewMethods: function() {
            const autoView = window.Hi.autoView;
            if (!autoView) return;

            // Store original methods
            this.originalMethods.recordInteraction = autoView.recordInteraction;
            this.originalMethods.navigateToTransientView = autoView.navigateToTransientView;
            this.originalMethods.revertToOriginalView = autoView.revertToOriginalView;

            // Intercept recordInteraction
            autoView.recordInteraction = (eventType) => {
                this.logEvent('INTERACTION', eventType || 'unknown');
                return this.originalMethods.recordInteraction.call(autoView, eventType);
            };

            // Intercept navigateToTransientView
            autoView.navigateToTransientView = (suggestion) => {
                this.logEvent('AUTO-SWITCH', `To: ${suggestion.url}`,
                    `${suggestion.durationSeconds}s, ${suggestion.triggerReason}`);
                return this.originalMethods.navigateToTransientView.call(autoView, suggestion);
            };

            // Intercept revertToOriginalView
            autoView.revertToOriginalView = () => {
                this.logEvent('REVERT', 'To original view');
                return this.originalMethods.revertToOriginalView.call(autoView);
            };
        },

        detectPlatform: function() {
            const platform = navigator.platform || 'Unknown';
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);

            let platformText = platform;
            if (isIOS) {
                platformText += ' (iOS)';
                if (isSafari) {
                    platformText += ' Safari';
                } else {
                    platformText += ' Chrome';
                }
            }

            const hasTouch = 'ontouchstart' in document.documentElement || navigator.maxTouchPoints > 0;

            this.updateValue('debug-platform', platformText);
            this.updateValue('debug-touch', hasTouch ? 'Yes' : 'No');
        },

        startUpdateLoop: function() {
            this.updateInterval = setInterval(() => {
                this.updateDisplay();
            }, this.UPDATE_INTERVAL_MS);

            this.updateDisplay(); // Initial update
        },

        updateDisplay: function() {
            const autoView = window.Hi.autoView;
            if (!autoView) return;

            // Calculate idle time
            const idleTime = Date.now() - autoView.lastInteractionTime;
            const idleSeconds = (idleTime / 1000).toFixed(1);

            // Determine status
            let status = 'ACTIVE';
            let statusClass = 'status-active';

            if (autoView.isTransientView) {
                status = 'TRANSIENT';
                statusClass = 'status-transient';
            } else if (idleSeconds >= autoView.IDLE_TIMEOUT_SECONDS) {
                status = 'IDLE';
                statusClass = 'status-idle';
            }

            // Update display
            const statusEl = document.getElementById('debug-status');
            if (statusEl) {
                statusEl.textContent = status;
                statusEl.className = `debug-value ${statusClass}`;
            }

            this.updateValue('debug-idle', `${idleSeconds}s / ${autoView.IDLE_TIMEOUT_SECONDS}s`);
            this.updateEventDisplay();
        },

        updateValue: function(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;
            }
        },

        logEvent: function(category, message, details = '') {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = {
                time: timestamp,
                category: category,
                message: message,
                details: details
            };

            this.eventLog.unshift(logEntry);

            if (this.eventLog.length > this.MAX_EVENT_LOG_SIZE) {
                this.eventLog = this.eventLog.slice(0, this.MAX_EVENT_LOG_SIZE);
            }
        },

        updateEventDisplay: function() {
            const eventsEl = document.getElementById('debug-events');
            if (!eventsEl) return;

            if (this.eventLog.length === 0) {
                eventsEl.textContent = 'No events';
                return;
            }

            const eventsHtml = this.eventLog.map(entry => {
                const details = entry.details ? ` (${entry.details})` : '';
                return `<div class="debug-event">
                    <div class="debug-event-time">${entry.time}</div>
                    ${entry.category}: ${entry.message}${details}
                </div>`;
            }).join('');

            eventsEl.innerHTML = eventsHtml;
        },

        toggleMinimize: function() {
            if (this.overlayElement) {
                this.overlayElement.classList.toggle('minimized');
            }
        },

        hide: function() {
            if (this.overlayElement) {
                this.overlayElement.style.display = 'none';
            }
            this.stopUpdateLoop();
        },

        show: function() {
            if (this.overlayElement) {
                this.overlayElement.style.display = 'block';
            }
            this.startUpdateLoop();
        },

        stopUpdateLoop: function() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
                this.updateInterval = null;
            }
        },

        destroy: function() {
            this.stopUpdateLoop();

            // Restore original methods
            const autoView = window.Hi.autoView;
            if (autoView && this.originalMethods) {
                Object.keys(this.originalMethods).forEach(methodName => {
                    if (this.originalMethods[methodName]) {
                        autoView[methodName] = this.originalMethods[methodName];
                    }
                });
            }

            if (this.overlayElement) {
                this.overlayElement.remove();
            }

            const styleEl = document.getElementById('auto-view-debug-styles');
            if (styleEl) {
                styleEl.remove();
            }

            this.isInitialized = false;
        }
    };

    // Initialize when auto-view is available
    waitForAutoView(() => {
        AutoViewDebug.init();
    });

    // Expose for debugging (optional)
    if (window.Hi.DEBUG) {
        window.Hi.autoViewDebug = AutoViewDebug;
    }

})();