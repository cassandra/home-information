// Entity Picker module for interactive filtering and search
// Used in Location View and Collection View editing modes
// Uses jQuery event delegation for dynamically loaded content

$(document).ready(function() {

    var EntityPicker = {

        // Current filter state
        currentFilter: Hi.ENTITY_PICKER_FILTER_ALL,
        searchTerm: '',

        // Apply current filters to visible items
        applyFilters: function() {
            // Find all filterable items using our unified class
            var $items = $(Hi.ENTITY_PICKER_FILTERABLE_ITEM_SELECTOR);
            var $groups = $(Hi.ENTITY_PICKER_GROUP_SECTION_SELECTOR);
            var self = this;
            var filtersActive = ( self.searchTerm !== ''
                                  || self.currentFilter !== Hi.ENTITY_PICKER_FILTER_ALL );

            $items.each(function() {
                var $item = $(this);
                var show = true;

                // Apply search filter
                if (self.searchTerm) {
                    var entityName = $item.attr(Hi.ENTITY_PICKER_DATA_NAME_ATTR) || '';
                    var entityType = $item.attr(Hi.ENTITY_PICKER_DATA_TYPE_ATTR) || '';
                    var searchableText = (entityName + ' ' + entityType).toLowerCase();

                    if (searchableText.indexOf(self.searchTerm) === -1) {
                        show = false;
                    }
                }

                // Apply status filter
                if (self.currentFilter !== Hi.ENTITY_PICKER_FILTER_ALL) {
                    var status = $item.attr(Hi.ENTITY_PICKER_DATA_STATUS_ATTR);

                    switch (self.currentFilter) {
                        case Hi.ENTITY_PICKER_STATUS_IN_VIEW:
                            if (status !== Hi.ENTITY_PICKER_STATUS_IN_VIEW) {
                                show = false;
                            }
                            break;
                        case Hi.ENTITY_PICKER_STATUS_NOT_IN_VIEW:
                            if (status === Hi.ENTITY_PICKER_STATUS_IN_VIEW || status === Hi.ENTITY_PICKER_STATUS_UNUSED) {
                                show = false;
                            }
                            break;
                        case Hi.ENTITY_PICKER_STATUS_UNUSED:
                            if (status !== Hi.ENTITY_PICKER_STATUS_UNUSED) {
                                show = false;
                            }
                            break;
                    }
                }

                // Show/hide item
                $item.toggle(show);
            });

            // Show/hide groups based on items that MATCH the current
            // filter -- using each item's own display rather than
            // ':visible'. A collapsed group's items are display:none via
            // Bootstrap's .collapse, so ':visible' reports zero matches
            // and would wrongly hide an otherwise-matching group (and
            // never reveal its matches). While a search/filter is active
            // we also force a matching group's body open so its matches
            // are actually shown; when cleared, we drop the override so
            // the group's own collapsed/expanded state governs again.
            $groups.each(function() {
                var $group = $(this);
                var $body = $group.find('.entity-group-items');
                var $header = $group.find('.entity-group-header');
                var matchCount = $group.find(Hi.ENTITY_PICKER_FILTERABLE_ITEM_SELECTOR).filter(function() {
                    return this.style.display !== 'none';
                }).length;

                if (matchCount === 0) {
                    $group.hide();
                    $body.css('display', '');
                    return;
                }

                $group.show();
                if (filtersActive) {
                    // Reveal matches even inside a collapsed group.
                    $body.css('display', 'block');
                    $header.attr('aria-expanded', 'true');
                } else {
                    // Restore the group's own collapse state (default or
                    // user-toggled), tracked by Bootstrap's 'show' class.
                    $body.css('display', '');
                    $header.attr('aria-expanded', $body.hasClass('show') ? 'true' : 'false');
                }
            });
        },

        // Set active filter
        setFilter: function(filter) {
            this.currentFilter = filter;

            // Update button states
            $(Hi.ENTITY_PICKER_FILTER_BTN_SELECTOR).removeClass('active');
            $(Hi.ENTITY_PICKER_FILTER_BTN_SELECTOR + '[' + Hi.ENTITY_PICKER_DATA_FILTER_ATTR + '="' + filter + '"]').addClass('active');

            this.applyFilters();
        },


        // Reset all filters and search
        reset: function() {
            this.searchTerm = '';
            this.currentFilter = Hi.ENTITY_PICKER_FILTER_ALL;

            $(Hi.ENTITY_PICKER_SEARCH_INPUT_SELECTOR).val('');
            this.setFilter(Hi.ENTITY_PICKER_FILTER_ALL);
        }
    };

    // Event delegation for search input
    $('body').on('input', Hi.ENTITY_PICKER_SEARCH_INPUT_SELECTOR, function() {
        var $input = $(this);
        EntityPicker.searchTerm = $input.val().toLowerCase().trim();
        EntityPicker.applyFilters();
    });

    // Event delegation for filter buttons
    $('body').on('click', Hi.ENTITY_PICKER_FILTER_BTN_SELECTOR, function(e) {
        e.preventDefault();
        var $button = $(this);
        var filter = $button.attr(Hi.ENTITY_PICKER_DATA_FILTER_ATTR);
        EntityPicker.setFilter(filter);
    });

    // Event delegation for search clear button
    $('body').on('click', Hi.ENTITY_PICKER_SEARCH_CLEAR_SELECTOR, function(e) {
        e.preventDefault();
        $(Hi.ENTITY_PICKER_SEARCH_INPUT_SELECTOR).val('');
        EntityPicker.searchTerm = '';
        EntityPicker.applyFilters();
    });


    // Make EntityPicker available globally
    window.HiEntityPicker = EntityPicker;

});