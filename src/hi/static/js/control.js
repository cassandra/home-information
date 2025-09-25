// Control module for all controller types
// Uses jQuery event delegation for dynamically loaded content

$(document).ready(function() {
    
    // Event delegation for on/off switch status update
    $('body').on('change', '.switch-input', function() {
        var $switch = $(this);
        var $statusText = $switch.closest('.on-off-control').find('.status-text');
        var isChecked = $switch.is(':checked');
        $statusText.text(isChecked ? 'On' : 'Off');
    });
    
    // Event delegation for discrete select status update
    $('body').on('change', '.discrete-select', function() {
        var $select = $(this);
        var value = $select.val();
        var $statusValue = $select.closest('.discrete-control').find('.status-value');
        $statusValue.text(value);
    });
    
    // Event delegation for brightness slider input (real-time display update)
    $('body').on('input', '.brightness-slider', function() {
        var $slider = $(this);
        var value = $slider.val();
        var $display = $slider.closest('.brightness-control').find('.brightness-value');
        $display.text(value + '%');
    });
    
    // Event delegation for brightness quick-set buttons
    $('body').on('click', '.brightness-btn', function() {
        var $button = $(this);
        var value = $button.data('value');
        var $control = $button.closest('.brightness-control');
        var $slider = $control.find('.brightness-slider');
        var $display = $control.find('.brightness-value');
        
        // Update slider value and display
        $slider.val(value);
        $display.text(value + '%');
        
        // Trigger the change event to submit form via existing onchange-async handler
        $slider.trigger('change');
    });
    
});
