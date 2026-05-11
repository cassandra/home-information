"""Console/UI boundary value translation.

Symmetric to ``IntegrationConverterHelper`` (which handles the
integration ↔ HI boundary): this helper handles the HI ↔ UI
boundary. The integration boundary keys conversions on
``IntegrationKey`` and consults the ``IntegrationMetadataCache``;
the UI boundary keys on ``EntityState`` and reads ``.units``
directly.

Direction conventions match the integration helper:
- ``to_entity_state_value(display_value, entity_state)``: inbound
  from the UI (a slider submission, a form field) — translate the
  user's display-unit value back to the EntityState's stored unit
  for caching and downstream dispatch.
- ``from_entity_state_value(value, entity_state)``: outbound to
  the UI — translate the EntityState's stored value to the user's
  preferred display unit, returning a structured ``DisplayValue``
  so callers can format magnitude / unit / combined text per
  their need.

Pass-through when the EntityState has no units (hue, percent,
on/off, etc.) so this helper is safe to call uniformly without
per-state-type branching at the call sites.
"""
import logging
from dataclasses import dataclass

from hi.apps.console.console_helper import ConsoleSettingsHelper
from hi.apps.entity.models import EntityState
from hi.units import UnitQuantity, get_display_quantity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DisplayValue:
    """A value formatted for UI display: separated magnitude and
    unit-symbol fields so callers can render each independently
    (e.g., a slider's numeric ``value=`` attribute uses just the
    magnitude; a status text element uses the combined string).

    ``__str__`` produces the combined form (``"69.8°F"``) for the
    common case of dropping it directly into a template."""

    magnitude    : str = ''
    unit_symbol  : str = ''

    def __str__(self):
        if not self.unit_symbol:
            return self.magnitude
        if not self.magnitude:
            return self.unit_symbol
        # NIST/SI convention: a space separates magnitude from
        # alphabetic unit abbreviations (``120 lx``, ``5 kg``).
        # Symbol-style units (``°F``, ``°C``, ``%``) attach
        # directly per common typographic practice.
        if self.unit_symbol[0].isalpha():
            return f'{self.magnitude} {self.unit_symbol}'
        return f'{self.magnitude}{self.unit_symbol}'


class ConsoleConverterHelper:

    @classmethod
    def to_entity_state_value(
            cls,
            display_value : str,
            entity_state  : EntityState,
    ) -> str:
        """Inbound boundary: translate a value submitted from the
        UI (form post, slider) — which is in the user's display
        unit — back to the EntityState's stored unit for caching
        and downstream dispatch. No-op when the EntityState has no
        units or when the display unit equals the stored unit.
        Non-numeric submissions are logged and passed through so
        downstream validation owns the rejection."""
        entity_state_unit_str = entity_state.units
        if not entity_state_unit_str:
            return display_value
        display_units = ConsoleSettingsHelper().get_display_units()
        entity_state_quantity = UnitQuantity( 0, entity_state_unit_str )
        display_unit = get_display_quantity(
            entity_state_quantity, display_units,
        ).units
        if display_unit == entity_state_quantity.units:
            return display_value
        try:
            display_value_float = float( display_value )
        except ( ValueError, TypeError ):
            logger.warning(
                f'Non-numeric value {display_value!r} submitted for'
                f' unit-bearing entity_state {entity_state.id};'
                f' skipping unit translation.'
            )
            return display_value
        display_quantity = UnitQuantity( display_value_float, display_unit )
        return str(
            display_quantity.to( entity_state_unit_str ).magnitude
        )

    @classmethod
    def from_entity_state_value(
            cls,
            entity_state_value,
            entity_state : EntityState,
    ) -> DisplayValue:
        """Outbound boundary: translate a value in the EntityState's
        stored unit to the user's preferred display unit, returning
        a ``DisplayValue`` (magnitude + unit_symbol). Pass-through
        when the EntityState has no units or the value can't be
        coerced — the magnitude is the input value as a string and
        the unit_symbol is empty, so the call is safe to make
        uniformly across all EntityState types."""
        if entity_state_value is None:
            return DisplayValue()
        raw_str = str( entity_state_value )
        units = getattr( entity_state, 'units', None )
        if not units:
            return DisplayValue( magnitude = raw_str )
        try:
            quantity = UnitQuantity( float( entity_state_value ), units )
        except Exception:
            return DisplayValue( magnitude = raw_str )
        display_units = ConsoleSettingsHelper().get_display_units()
        display_quantity = get_display_quantity( quantity, display_units )
        try:
            magnitude = str( round( display_quantity.magnitude, 1 ) )
        except Exception:
            magnitude = raw_str
        try:
            unit_symbol = f'{display_quantity.units:~P}'
        except Exception:
            unit_symbol = ''
        return DisplayValue( magnitude = magnitude, unit_symbol = unit_symbol )
