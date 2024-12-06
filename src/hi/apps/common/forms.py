from dataclasses import dataclass

from django.forms import BaseInlineFormSet


@dataclass
class FormsetStats:
    total_forms      : int  = 0
    deleted_forms    : int  = 0
    bound_forms      : int  = 0
    valid_forms      : int  = 0
    error_forms      : int  = 0
    changed_forms    : int  = 0
    extra_forms      : int  = 0

    @property
    def has_at_least_one(self):
        return bool(
            (( self.total_forms - self.extra_forms - self.deleted_forms ) > 0 )
            or ( self.changed_forms > 0 )
        )
    

class CustomBaseFormSet( BaseInlineFormSet ):
    _is_valid_cache = None

    def is_valid(self):
        """Cache the result of formset validation to avoid repeated checks."""
        if self._is_valid_cache is None:
            self._is_valid_cache = super().is_valid()
        return self._is_valid_cache

    def get_formset_stats(self) -> FormsetStats:
        self.is_valid()  # Ensure cleaned_data exists

        formset_stats = FormsetStats()
        formset_stats.extra_forms = self.extra
        
        for form in self.forms:
            formset_stats.total_forms += 1

            if form.cleaned_data.get( 'DELETE', False ):
                formset_stats.deleted_forms += 1
            elif form.has_changed():
                formset_stats.changed_forms += 1
                
            if bool( form.instance.pk ):
                formset_stats.bound_forms += 1
            if form.errors:
                formset_stats.error_forms += 1
            else:
                formset_stats.valid_forms += 1
            continue
        return formset_stats
