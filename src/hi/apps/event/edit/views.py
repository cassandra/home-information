from django.db import transaction
from django.urls import reverse

from hi.apps.event.view_mixin import EventViewMixin
import hi.apps.event.forms as forms

from hi.hi_async_view import HiModalView


class EventDefinitionEditView( HiModalView, EventViewMixin ):

    def get_template_name( self ) -> str:
        return 'event/edit/modals/event_definition_edit.html'
    
    def get( self, request, *args, **kwargs ):
        event_definition = self.get_event_definition( request, *args, **kwargs )

        event_definition_form = forms.EventDefinitionForm(
            instance = event_definition,
        )
        event_clause_formset = forms.EventClauseFormSet(
            instance = event_definition,
            prefix = self.EVENT_CLAUSE_FORMSET_PREFIX,
        )
        alarm_action_formset = forms.AlarmActionFormSet(
            instance = event_definition,
            prefix = self.ALARM_ACTION_FORMSET_PREFIX,
        )
        control_action_formset = forms.ControlActionFormSet(
            instance = event_definition,
            prefix = self.CONTROL_ACTION_FORMSET_PREFIX,
        )
        
        context = {
            'event_definition': event_definition,
            'event_definition_form': event_definition_form,
            'event_clause_formset': event_clause_formset,
            'alarm_action_formset': alarm_action_formset,
            'control_action_formset': control_action_formset,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        event_definition = self.get_event_definition( request, *args, **kwargs )

        event_definition_form = forms.EventDefinitionForm(
            request.POST,
            instance = event_definition,
        )
        event_clause_formset = forms.EventClauseFormSet(
            request.POST,
            request.FILES,
            instance = event_definition,
            prefix = self.EVENT_CLAUSE_FORMSET_PREFIX,
        )
        alarm_action_formset = forms.AlarmActionFormSet(
            request.POST,
            request.FILES,
            instance = event_definition,
            prefix = self.ALARM_ACTION_FORMSET_PREFIX,
        )
        control_action_formset = forms.ControlActionFormSet(
            request.POST,
            request.FILES,
            instance = event_definition,
            prefix = self.CONTROL_ACTION_FORMSET_PREFIX,
        )

        def error_response():
            context = {
                'event_definition_form': event_definition_form,
                'event_clause_formset': event_clause_formset,
                'alarm_action_formset': alarm_action_formset,
                'control_action_formset': control_action_formset,
            }
            return self.modal_response( request, context )
            
        if ( not event_definition_form.is_valid()
             or not event_clause_formset.is_valid()
             or not alarm_action_formset.is_valid()
             or not control_action_formset.is_valid() ):
            return error_response()
        
        event_clause_formset_stats = event_clause_formset.get_formset_stats()
        alarm_action_formset_stats = alarm_action_formset.get_formset_stats()
        control_action_formset_stats = control_action_formset.get_formset_stats()





        
        #print( f'\n\nEventClause   : {event_clause_formset_stats}' )
        #print( f'AlarmAction   : {alarm_action_formset_stats}' )
        #print( f'ControlAction : {control_action_formset_stats}\n\n' )
        #redirect_url = reverse( 'event_definitions' )
        #return self.redirect_response( request = request,
        #                               redirect_url = redirect_url )






        all_forms_valid = True
        if not event_clause_formset_stats.has_at_least_one:
            all_forms_valid = False
            event_definition_form.add_error(
                None, 'Must have at least one event clause.'
            )
                
        if ( not alarm_action_formset_stats.has_at_least_one 
             and not control_action_formset_stats.has_at_least_one ):
            all_forms_valid = False
            event_definition_form.add_error(
                None, 'Must have either alarm of control action.'
            )

        if not all_forms_valid:
            return error_response()
            
        with transaction.atomic():
            event_definition = event_definition_form.save()

            # Need to force the instance so forms can save with foreign key
            event_clause_formset.instance = event_definition
            alarm_action_formset.instance = event_definition
            control_action_formset.instance = event_definition
            
            event_clause_formset.save()
            alarm_action_formset.save()
            control_action_formset.save()
            
        redirect_url = reverse( 'event_definitions' )
        return self.redirect_response( request = request,
                                       redirect_url = redirect_url )
            
    
class EventDefinitionAddView( EventDefinitionEditView ):

    def get_template_name( self ) -> str:
        return 'event/edit/modals/event_definition_add.html'

    def get_event_definition( self, request, *args, **kwargs  ) -> str:
        return None

    
class EventDefinitionDeleteView( HiModalView, EventViewMixin ):

    def get_template_name( self ) -> str:
        return 'event/edit/modals/event_definition_delete.html'
    
    def get( self, request, *args, **kwargs ):
        event_definition = self.get_event_definition( request, *args, **kwargs )
        context = {
            'event_definition': event_definition,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        event_definition = self.get_event_definition( request, *args, **kwargs )
        event_definition.delete()
        return zzz
