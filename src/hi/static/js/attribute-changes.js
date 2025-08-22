// Attribute Changes Tracker
// Provides visual indicators for unsaved attribute changes
// Copyright 2024 by POMDP, Inc. - All rights reserved

(function($) {
    'use strict';

    // Namespace for attribute change tracking
    const AttributeChanges = {
        
        // Configuration
        config: {
            modifiedClass: 'attribute-modified',
            indicatorClass: 'attribute-modified-indicator',
            bannerClass: 'unsaved-changes-banner',
            debounceDelay: 300
        },

        // State tracking
        state: {
            originalValues: new Map(),
            modifiedFields: new Set(),
            hasUnsavedChanges: false,
            beforeUnloadWarning: false,
            debounceTimers: new Map()
        },

        // Initialize the change tracking system
        init: function() {
            this.captureOriginalValues();
            this.bindEvents();
            this.setupNavigationWarning();
        },

        // Capture original values for all attribute fields
        captureOriginalValues: function() {
            const self = this;
            
            // Find all attribute form fields
            $('.hi-attribute-list').find('input, textarea, select').each(function() {
                const $field = $(this);
                const fieldId = $field.attr('id');
                
                if (fieldId && !fieldId.endsWith('-show')) { // Skip password show/hide checkboxes
                    let originalValue = self.getFieldValue($field);
                    self.state.originalValues.set(fieldId, originalValue);
                    
                    // Add data attribute for reference
                    $field.attr('data-original-value', originalValue);
                }
            });
        },

        // Get normalized field value based on field type
        getFieldValue: function($field) {
            const fieldType = $field.prop('type');
            const tagName = $field.prop('tagName').toLowerCase();
            
            if (fieldType === 'checkbox') {
                return $field.is(':checked') ? 'true' : 'false';
            } else if (tagName === 'select') {
                return $field.val() || '';
            } else {
                // For text fields and textareas, normalize whitespace
                return ($field.val() || '').trim();
            }
        },

        // Check if field has changed from original value
        hasFieldChanged: function($field) {
            const fieldId = $field.attr('id');
            const originalValue = this.state.originalValues.get(fieldId);
            const currentValue = this.getFieldValue($field);
            
            return originalValue !== currentValue;
        },

        // Bind event listeners
        bindEvents: function() {
            const self = this;
            
            // Handle input changes with debouncing for text fields
            $('.hi-attribute-list').on('input keyup', 'input[type="text"], input[type="password"], textarea', function() {
                const $field = $(this);
                const fieldId = $field.attr('id');
                
                // Clear existing debounce timer
                if (self.state.debounceTimers.has(fieldId)) {
                    clearTimeout(self.state.debounceTimers.get(fieldId));
                }
                
                // Set new debounce timer
                const timer = setTimeout(function() {
                    self.handleFieldChange($field);
                    self.state.debounceTimers.delete(fieldId);
                }, self.config.debounceDelay);
                
                self.state.debounceTimers.set(fieldId, timer);
            });

            // Handle immediate changes for select and checkbox
            $('.hi-attribute-list').on('change', 'select, input[type="checkbox"]', function() {
                self.handleFieldChange($(this));
            });

            // Handle form submission to clear indicators
            $('form').on('submit', function() {
                self.clearAllIndicators();
            });

            // Handle successful async form submission (using antinode.js pattern)
            $(document).on('an:success', function() {
                self.clearAllIndicators();
            });
        },

        // Handle individual field change
        handleFieldChange: function($field) {
            const fieldId = $field.attr('id');
            
            if (!fieldId || fieldId.endsWith('-show')) {
                return; // Skip password show/hide checkboxes
            }
            
            const hasChanged = this.hasFieldChanged($field);
            
            if (hasChanged) {
                this.addFieldIndicator($field);
                this.state.modifiedFields.add(fieldId);
            } else {
                this.removeFieldIndicator($field);
                this.state.modifiedFields.delete(fieldId);
            }
            
            this.updatePageState();
        },

        // Add visual indicator to field
        addFieldIndicator: function($field) {
            const $container = $field.closest('.input-group, div');
            
            // Add modified class to field
            $field.addClass(this.config.modifiedClass);
            
            // Add asterisk indicator if not already present
            if ($container.find('.' + this.config.indicatorClass).length === 0) {
                const $indicator = $('<span class="' + this.config.indicatorClass + '">*</span>');
                
                // Find the best place to insert the indicator
                const $label = $container.find('.input-group-text').first();
                if ($label.length > 0) {
                    $label.append(' ').append($indicator);
                } else {
                    $container.append($indicator);
                }
            }
        },

        // Remove visual indicator from field
        removeFieldIndicator: function($field) {
            const $container = $field.closest('.input-group, div');
            
            // Remove modified class
            $field.removeClass(this.config.modifiedClass);
            
            // Remove asterisk indicator
            $container.find('.' + this.config.indicatorClass).remove();
        },

        // Update page-level state (banner, title, warnings)
        updatePageState: function() {
            const hasChanges = this.state.modifiedFields.size > 0;
            
            if (hasChanges !== this.state.hasUnsavedChanges) {
                this.state.hasUnsavedChanges = hasChanges;
                
                if (hasChanges) {
                    this.showUnsavedChangesBanner();
                    this.enableNavigationWarning();
                    this.updatePageTitle(true);
                } else {
                    this.hideUnsavedChangesBanner();
                    this.disableNavigationWarning();
                    this.updatePageTitle(false);
                }
            }
        },

        // Show unsaved changes banner
        showUnsavedChangesBanner: function() {
            if ($('.' + this.config.bannerClass).length === 0) {
                const changeCount = this.state.modifiedFields.size;
                const message = `You have ${changeCount} unsaved change${changeCount !== 1 ? 's' : ''}`;
                
                const $banner = $(`
                    <div class="${this.config.bannerClass} alert alert-warning alert-dismissible fade show" role="alert">
                        <strong>Unsaved Changes:</strong> ${message}
                        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                `);
                
                // Insert at the top of the form
                $('.hi-attribute-list').before($banner);
            }
        },

        // Hide unsaved changes banner
        hideUnsavedChangesBanner: function() {
            $('.' + this.config.bannerClass).remove();
        },

        // Update page title with unsaved indicator
        updatePageTitle: function(hasUnsaved) {
            const title = document.title;
            
            if (hasUnsaved && !title.startsWith('* ')) {
                document.title = '* ' + title;
            } else if (!hasUnsaved && title.startsWith('* ')) {
                document.title = title.substring(2);
            }
        },

        // Setup beforeunload warning
        setupNavigationWarning: function() {
            const self = this;
            
            $(window).on('beforeunload', function(e) {
                if (self.state.beforeUnloadWarning && self.state.hasUnsavedChanges) {
                    const message = 'You have unsaved changes. Are you sure you want to leave?';
                    e.originalEvent.returnValue = message;
                    return message;
                }
            });
        },

        // Enable navigation warning
        enableNavigationWarning: function() {
            this.state.beforeUnloadWarning = true;
        },

        // Disable navigation warning
        disableNavigationWarning: function() {
            this.state.beforeUnloadWarning = false;
        },

        // Clear all indicators and reset state
        clearAllIndicators: function() {
            const self = this;
            
            // Clear all visual indicators
            $('.' + this.config.modifiedClass).removeClass(this.config.modifiedClass);
            $('.' + this.config.indicatorClass).remove();
            
            // Clear state
            this.state.modifiedFields.clear();
            this.state.hasUnsavedChanges = false;
            
            // Clear page-level indicators
            this.hideUnsavedChangesBanner();
            this.disableNavigationWarning();
            this.updatePageTitle(false);
            
            // Clear debounce timers
            this.state.debounceTimers.forEach(function(timer) {
                clearTimeout(timer);
            });
            this.state.debounceTimers.clear();
        },

        // Public method to manually refresh original values (for dynamic content)
        refreshOriginalValues: function() {
            this.clearAllIndicators();
            this.state.originalValues.clear();
            this.captureOriginalValues();
        }
    };

    // Initialize when DOM is ready
    $(document).ready(function() {
        // Only initialize if we're on a page with attributes
        if ($('.hi-attribute-list').length > 0) {
            AttributeChanges.init();
        }
    });

    // Add to Hi namespace for potential external access
    if (window.Hi) {
        window.Hi.AttributeChanges = AttributeChanges;
    }

})(jQuery);