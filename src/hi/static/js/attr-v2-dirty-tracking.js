/*
 * Home Information - Attribute V2 Dirty State Tracking
 * Comprehensive dirty state tracking for V2 entity attribute editing modal
 * Handles field-level changes with proper V2 pattern support
 */

(function() {
    'use strict';
    
    // Create namespace
    window.attrV2 = window.attrV2 || {};
    window.attrV2.DirtyTracking = {
        
        // Configuration
        config: {
            formSelector: Hi.ATTR_V2_FORM_SELECTOR,
            messageContainerSelector: Hi.ATTR_V2_DIRTY_MESSAGE_SELECTOR,
            debounceDelay: 300,
            dirtyFieldClass: Hi.ATTR_V2_FIELD_DIRTY_CLASS,
            dirtyIndicatorClass: Hi.ATTR_V2_DIRTY_INDICATOR_CLASS
        },
        
        // State
        state: {
            originalValues: new Map(),
            dirtyFields: new Set(),
            debounceTimers: new Map(),
            isInitialized: false
        },
        
        // Initialize the dirty tracking system
        init: function() {
            if (this.state.isInitialized) {
                return;
            }
            
            const form = document.querySelector(this.config.formSelector);
            if (!form) {
                return;
            }
            
            this.captureOriginalValues();
            this.bindEvents();
            this.state.isInitialized = true;
        },
        
        // Capture original values for all form fields
        captureOriginalValues: function() {
            const form = document.querySelector(this.config.formSelector);
            if (!form) return;
            
            // Entity name field
            const entityNameField = form.querySelector('input[name$="name"]:not([name*="-"])');
            if (entityNameField) {
                this.captureFieldValue(entityNameField);
            }
            
            // Attribute form fields
            const attributeFields = form.querySelectorAll(`${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} input, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} textarea, ${Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR} select`);
            attributeFields.forEach(field => {
                // Skip hidden management form fields
                if (field.type === 'hidden' && field.name.includes('_')) return;
                this.captureFieldValue(field);
            });
            
            // File title input fields
            const fileTitleFields = form.querySelectorAll(Hi.ATTR_V2_FILE_TITLE_INPUT_SELECTOR);
            fileTitleFields.forEach(field => {
                this.captureFieldValue(field);
            });
        },
        
        // Capture individual field value
        captureFieldValue: function(field) {
            if (!field.name || !field.id) return;
            
            let originalValue = this.getFieldValue(field);
            this.state.originalValues.set(field.id, originalValue);
            field.setAttribute('data-original-value', originalValue);
        },
        
        // Get normalized field value
        getFieldValue: function(field) {
            if (field.type === 'checkbox') {
                return field.checked ? 'true' : 'false';
            } else if (field.tagName.toLowerCase() === 'select') {
                return field.value || '';
            } else {
                return (field.value || '').trim();
            }
        },
        
        // Check if field has changed
        hasFieldChanged: function(field) {
            const originalValue = this.state.originalValues.get(field.id);
            const currentValue = this.getFieldValue(field);
            
            // Special handling for new attribute forms - consider them dirty if they have content
            const isNewAttributeField = field.closest(Hi.ATTR_V2_NEW_ATTRIBUTE_SELECTOR);
            if (isNewAttributeField && field.name.includes('-name') && currentValue.length > 0) {
                return true;
            }
            
            return originalValue !== currentValue;
        },
        
        // Bind event listeners
        bindEvents: function() {
            const form = document.querySelector(this.config.formSelector);
            if (!form) return;
            
            // Text input changes with debouncing
            this.bindDebouncedEvents(form, 'input[type="text"], input[type="password"], input[type="number"], textarea', 'input');
            
            // Immediate changes for selects and checkboxes
            this.bindImmediateEvents(form, 'select, input[type="checkbox"]', 'change');
            
            // Form submission handling
            form.addEventListener('submit', this.handleFormSubmission.bind(this));
            
            // Handle file title input activation (persistent styling on first interaction)
            form.addEventListener('focus', (e) => {
                if (e.target.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                    e.target.classList.add('activated');
                }
            }, true); // Use capture phase to ensure we catch the event
            
            // Handle successful form submission (antinode.js pattern)
            document.addEventListener('an:success', this.handleFormSuccess.bind(this));
        },
        
        // Bind debounced events for text inputs
        bindDebouncedEvents: function(form, selector, eventType) {
            form.addEventListener(eventType, (e) => {
                if (!e.target.matches(selector)) return;
                
                const field = e.target;
                const fieldId = field.id;
                
                if (!fieldId) return;
                
                // Clear existing timer
                if (this.state.debounceTimers.has(fieldId)) {
                    clearTimeout(this.state.debounceTimers.get(fieldId));
                }
                
                // Set new timer
                const timer = setTimeout(() => {
                    this.handleFieldChange(field);
                    this.state.debounceTimers.delete(fieldId);
                }, this.config.debounceDelay);
                
                this.state.debounceTimers.set(fieldId, timer);
            });
        },
        
        // Bind immediate events for selects and checkboxes
        bindImmediateEvents: function(form, selector, eventType) {
            form.addEventListener(eventType, (e) => {
                if (!e.target.matches(selector)) return;
                this.handleFieldChange(e.target);
            });
        },
        
        // Handle individual field change
        handleFieldChange: function(field) {
            const hasChanged = this.hasFieldChanged(field);
            
            if (hasChanged) {
                this.markFieldDirty(field);
                this.state.dirtyFields.add(field.id);
            } else {
                this.clearFieldDirty(field);
                this.state.dirtyFields.delete(field.id);
            }
            
            this.updateMessageArea();
        },
        
        // Mark field as dirty with visual indicators
        markFieldDirty: function(field) {
            field.classList.add(this.config.dirtyFieldClass);
            
            // For file title inputs, add activated class for persistent styling
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                field.classList.add('activated');
            }
            
            // Add indicator to field container
            const container = this.getFieldContainer(field);
            if (container && !container.querySelector('.' + this.config.dirtyIndicatorClass)) {
                const indicator = this.createDirtyIndicator();
                this.insertDirtyIndicator(container, indicator);
                
                // Add fallback CSS classes for browsers without :has() support
                this.addFallbackClasses(container, field);
            }
        },
        
        // Clear dirty state from field
        clearFieldDirty: function(field) {
            field.classList.remove(this.config.dirtyFieldClass);
            
            // Remove indicator
            const container = this.getFieldContainer(field);
            if (container) {
                const indicator = container.querySelector('.' + this.config.dirtyIndicatorClass);
                if (indicator) {
                    indicator.remove();
                }
                
                // Remove fallback CSS classes
                this.removeFallbackClasses(container, field);
            }
        },
        
        // Get appropriate container for field indicator
        getFieldContainer: function(field) {
            // For file title inputs, use the file info container
            if (field.classList.contains(Hi.ATTR_V2_FILE_TITLE_INPUT_CLASS)) {
                const fileInfo = field.closest(Hi.ATTR_V2_FILE_INFO_SELECTOR);
                if (fileInfo) {
                    return field; // Use the input itself as container for positioning
                }
            }
            
            // For attribute cards, use the attribute header
            const attributeCard = field.closest(Hi.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
            if (attributeCard) {
                return attributeCard.querySelector(Hi.ATTR_V2_ATTRIBUTE_NAME_SELECTOR);
            }
            
            // For entity name, use the form group
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                return formGroup.querySelector('small, label') || formGroup;
            }
            
            return field.parentElement;
        },
        
        // Create dirty indicator element
        createDirtyIndicator: function() {
            const indicator = document.createElement('span');
            indicator.className = this.config.dirtyIndicatorClass;
            indicator.innerHTML = '●'; // Simple dot indicator
            indicator.title = 'This field has been modified';
            return indicator;
        },
        
        // Insert dirty indicator in appropriate position
        insertDirtyIndicator: function(container, indicator) {
            // For attribute names, append to the end
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.appendChild(indicator);
            } else {
                // For other containers, insert at the end
                container.appendChild(indicator);
            }
        },
        
        // Add fallback CSS classes for browsers without :has() support
        addFallbackClasses: function(container, field) {
            // For attribute names
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.add('has-dirty-indicator');
            }
            
            // For form groups (entity name)
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.add('has-dirty-field');
            }
        },
        
        // Remove fallback CSS classes
        removeFallbackClasses: function(container, field) {
            // For attribute names
            if (container.classList.contains(Hi.ATTR_V2_ATTRIBUTE_NAME_CLASS)) {
                container.classList.remove('has-dirty-indicator');
            }
            
            // For form groups (entity name)
            const formGroup = field.closest('.form-group');
            if (formGroup) {
                formGroup.classList.remove('has-dirty-field');
            }
        },
        
        // Update message area with current dirty state
        updateMessageArea: function() {
            const messageContainer = document.querySelector(this.config.messageContainerSelector);
            if (!messageContainer) return;
            
            const dirtyCount = this.state.dirtyFields.size;
            
            if (dirtyCount === 0) {
                messageContainer.textContent = '';
                messageContainer.className = Hi.ATTR_V2_DIRTY_MESSAGE_CLASS;
            } else {
                const message = dirtyCount === 1 
                    ? '1 field modified' 
                    : `${dirtyCount} fields modified`;
                messageContainer.textContent = message;
                messageContainer.className = Hi.ATTR_V2_DIRTY_MESSAGE_CLASS + ' active';
            }
        },
        
        // Handle form submission
        handleFormSubmission: function(e) {
            // Handle textarea sync for truncated/hidden field pattern
            this.syncDisplayToHiddenFields();
        },
        
        // Sync display fields to hidden fields before submission
        syncDisplayToHiddenFields: function() {
            const form = document.querySelector(this.config.formSelector);
            if (!form) return;
            
            const displayFields = form.querySelectorAll('.display-field');
            displayFields.forEach(displayField => {
                const hiddenFieldId = displayField.getAttribute('data-hidden-field');
                const hiddenField = hiddenFieldId ? document.getElementById(hiddenFieldId) : null;
                
                if (hiddenField && !displayField.readOnly && !displayField.classList.contains('truncated')) {
                    hiddenField.value = displayField.value;
                }
            });
        },
        
        // Handle successful form submission
        handleFormSuccess: function(e) {
            this.clearAllDirtyState();
        },
        
        // Clear all dirty state
        clearAllDirtyState: function() {
            // Clear visual indicators
            const form = document.querySelector(this.config.formSelector);
            if (form) {
                form.querySelectorAll('.' + this.config.dirtyFieldClass).forEach(field => {
                    field.classList.remove(this.config.dirtyFieldClass);
                });
                
                form.querySelectorAll('.' + this.config.dirtyIndicatorClass).forEach(indicator => {
                    indicator.remove();
                });
                
                // Clear fallback classes
                form.querySelectorAll('.has-dirty-indicator').forEach(element => {
                    element.classList.remove('has-dirty-indicator');
                });
                
                form.querySelectorAll('.has-dirty-field').forEach(element => {
                    element.classList.remove('has-dirty-field');
                });
            }
            
            // Clear state
            this.state.dirtyFields.clear();
            
            // Clear timers
            this.state.debounceTimers.forEach(timer => clearTimeout(timer));
            this.state.debounceTimers.clear();
            
            // Clear message
            this.updateMessageArea();
        },
        
        // Reinitialize for dynamic content (called by modal system)
        reinitialize: function() {
            this.clearAllDirtyState();
            this.state.originalValues.clear();
            this.state.isInitialized = false;
            this.init();
        }
    };
    
    // Auto-initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        window.attrV2.DirtyTracking.init();
    });
    
    // Initialize after modal shown
    document.addEventListener('shown.bs.modal', function(e) {
        if (document.querySelector(Hi.ATTR_V2_FORM_SELECTOR)) {
            window.attrV2.DirtyTracking.reinitialize();
        }
    });
    
    // Hook into antinode success to reinitialize
    document.addEventListener('an:success', function(e) {
        if (document.querySelector(Hi.ATTR_V2_FORM_SELECTOR)) {
            // Delay to allow DOM updates
            setTimeout(() => {
                window.attrV2.DirtyTracking.reinitialize();
            }, 100);
        }
    });
    
})();
