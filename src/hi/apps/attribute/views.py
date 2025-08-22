from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.views import page_not_found_response
from .models import AttributeModel


class AttributeHistoryView(View):
    """View for displaying attribute history in a modal."""
    
    def get(self, request, attribute_id, *args, **kwargs):
        try:
            # Get the specific attribute - this works for all attribute subclasses
            # since they all inherit from AttributeModel
            attribute = AttributeModel.objects.select_subclasses().get(pk=attribute_id)
        except AttributeModel.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        # Get history records for this attribute
        history_model_class = attribute._get_history_model_class()
        if history_model_class:
            history_records = history_model_class.objects.filter(
                attribute=attribute
            ).order_by('-changed_datetime')[:20]  # Limit to recent 20 records
        else:
            history_records = []
        
        context = {
            'attribute': attribute,
            'history_records': history_records,
        }
        
        return render(request, 'attribute/modals/attribute_history.html', context)


class AttributeRestoreView(View):
    """View for restoring attribute values from history."""
    
    def post(self, request, attribute_id, *args, **kwargs):
        try:
            attribute = AttributeModel.objects.select_subclasses().get(pk=attribute_id)
        except AttributeModel.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        history_id = request.POST.get('history_id')
        if not history_id:
            return page_not_found_response(request, "History record not specified.")
        
        # Get the history record to restore from
        history_model_class = attribute._get_history_model_class()
        if not history_model_class:
            return page_not_found_response(request, "No history available for this attribute type.")
            
        try:
            history_record = history_model_class.objects.get(pk=history_id, attribute=attribute)
        except history_model_class.DoesNotExist:
            return page_not_found_response(request, "History record not found.")
        
        # Restore the value from the history record
        attribute.value = history_record.value
        attribute.save()  # This will create a new history record
        
        # Return success response that triggers page reload
        return antinode.refresh_response(request)
