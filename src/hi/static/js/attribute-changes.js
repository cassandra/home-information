// Attribute Changes Tracker
// Provides visual indicators for unsaved attribute changes

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
            debounceTimers: new Map()
        },

        // Initialize the change tracking system
        init: function() {
            this.captureOriginalValues();
            this.bindEvents();
        },

        // Capture original values for all attribute fields
        captureOriginalValues: function() {
            const self = this;
            
            // Find all attribute form fields
            $('.hi-attribute-list').find('input, textarea, select').each(function() {
                const $field = $(this);
                const fieldId = $field.attr('id');
                
                if (fieldId && !fieldId.endsWith('-show')) { // Skip password show/hide checkboxes
                    // Only capture if we don't already have this field tracked
                    if (!self.state.originalValues.has(fieldId)) {
                        let originalValue = self.getFieldValue($field);
                        self.state.originalValues.set(fieldId, originalValue);
                        
                        // Add data attribute for reference
                        $field.attr('data-original-value', originalValue);
                    }
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

        // Bind event listeners using document-level delegation
        bindEvents: function() {
            const self = this;
            
            // Handle input changes with debouncing for text fields
            // Use document-level delegation to handle dynamically loaded forms
            $(document).on('input keyup', '.hi-attribute-list input[type="text"], .hi-attribute-list input[type="password"], .hi-attribute-list textarea', function() {
                const $field = $(this);
                const fieldId = $field.attr('id');
                
                // Skip if no ID (shouldn't happen for attribute fields)
                if (!fieldId) return;
                
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
            $(document).on('change', '.hi-attribute-list select, .hi-attribute-list input[type="checkbox"]', function() {
                self.handleFieldChange($(this));
            });

            // Handle form submission to clear indicators
            $(document).on('submit', 'form', function() {
                // Only clear if this form contains attributes
                if ($(this).find('.hi-attribute-list').length > 0) {
                    self.clearAllIndicators();
                }
            });

            // Handle successful async form submission (using antinode.js pattern)
            $(document).on('an:success', function(e) {
                // More conservative approach - only clear if we actually have unsaved changes
                // This prevents clearing indicators from unrelated Ajax success events
                if (self.state.hasUnsavedChanges) {
                    self.clearAllIndicators();
                }
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
                    this.updatePageTitle(true);
                } else {
                    this.hideUnsavedChangesBanner();
                    this.updatePageTitle(false);
                }
            }
        },

        // Show unsaved changes banner
        showUnsavedChangesBanner: function() {
            const changeCount = this.state.modifiedFields.size;
            const message = `You have ${changeCount} unsaved change${changeCount !== 1 ? 's' : ''}`;
            
            // Remove existing banner to avoid duplicates
            this.hideUnsavedChangesBanner();
            
            // Create new banner (removed dismissible to prevent state sync issues)
            const $banner = $(`
                <div class="${this.config.bannerClass} alert alert-warning fade show" role="alert">
                    <strong>Unsaved Changes:</strong> ${message}
                </div>
            `);
            
            // Insert at the top of the first attribute form
            $('.hi-attribute-list').first().before($banner);
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
        },

        // Initialize tracking for newly loaded attribute forms
        initializeNewForms: function() {
            // Capture original values for any new forms
            this.captureOriginalValues();
        }
    };

    // Initialize when DOM is ready
    $(document).ready(function() {
        // Always initialize - event delegation works without existing elements
        AttributeChanges.init();
    });

    // Hook into antinode async content loading to handle dynamic forms
    $(document).on('an:success', function() {
        // Reinitialize to capture original values for any newly loaded forms
        AttributeChanges.initializeNewForms();
    });

    // Add to Hi namespace for potential external access
    if (window.Hi) {
        window.Hi.AttributeChanges = AttributeChanges;
    }

})(jQuery);