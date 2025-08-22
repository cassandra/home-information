from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.views import page_not_found_response
from hi.hi_async_view import HiModalView


class BaseAttributeHistoryView(HiModalView):
    """
    Abstract base view for displaying attribute history in a modal.
    Subclasses must implement get_attribute_model_class(), get_history_url_name(), and get_restore_url_name().
    """
    
    def get_template_name(self):
        return 'attribute/modals/attribute_history.html'
    
    def get_attribute_model_class(self):
        """
        Return the concrete attribute model class for this view.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_attribute_model_class()"
        )
    
    def get_history_url_name(self):
        """
        Return the URL name for the history view.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_history_url_name()"
        )
    
    def get_restore_url_name(self):
        """
        Return the URL name for the restore view.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_restore_url_name()"
        )
    
    def get(self, request, attribute_id, *args, **kwargs):
        model_class = self.get_attribute_model_class()
        
        try:
            # Get the specific attribute using the concrete model class
            attribute = model_class.objects.get(pk=attribute_id)
        except model_class.DoesNotExist:
            return page_not_found_response(request, "Attribute not found.")
        
        # Get history records for this attribute
        history_model_class = attribute._get_history_model_class()
        if history_model_class:
            history_records = history_model_class.objects.filter(
                attribute=attribute
            ).order_by('-changed_datetime')[:500]  # High limit for safety, pagination TBD
        else:
            history_records = []
        
        context = {
            'attribute': attribute,
            'history_records': history_records,
            'history_url_name': self.get_history_url_name(),
            'restore_url_name': self.get_restore_url_name(),
        }
        
        return self.modal_response(request, context)


class BaseAttributeRestoreView(View):
    """
    Abstract base view for restoring attribute values from history.
    Subclasses must implement get_attribute_model_class().
    """
    
    def get_attribute_model_class(self):
        """
        Return the concrete attribute model class for this view.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_attribute_model_class()"
        )
    
    def post(self, request, attribute_id, *args, **kwargs):
        model_class = self.get_attribute_model_class()
        
        try:
            attribute = model_class.objects.get(pk=attribute_id)
        except model_class.DoesNotExist:
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
        return antinode.refresh_response()
