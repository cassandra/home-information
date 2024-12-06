from django.forms import BaseInlineFormSet


class CustomBaseFormSet( BaseInlineFormSet ):
    _is_valid_cache = None

    def is_valid(self):
        """Cache the result of formset validation to avoid repeated checks."""
        if self._is_valid_cache is None:
            self._is_valid_cache = super().is_valid()
        return self._is_valid_cache

    @property
    def has_at_least_one(self) -> bool:
        self.is_valid()  # Ensure cleaned_data exists

        total_forms = 0
        deleted_forms = 0
        changed_forms = 0
        
        for form in self.forms:
            total_forms += 1
            if form.cleaned_data.get( 'DELETE', False ):
                deleted_forms += 1
            elif form.has_changed():
                changed_forms += 1
            continue
        
        return bool((( total_forms - self.extra - deleted_forms ) > 0 )
                    or ( changed_forms > 0 ))
