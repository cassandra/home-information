import logging

from hi.apps.weather.wmo_units import WmoUnits
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWmoUnits(BaseTestCase):

    def test_normalize_unit_basic_functionality(self):
        """Test basic unit normalization without prefixes"""
        for wmo_unit_def in WmoUnits.UNIT_DEFINITIONS:
            for wmo_unit in [wmo_unit_def.get('wmoAbbrev'), wmo_unit_def.get('wmoAbbrev2')]:
                if not wmo_unit:
                    continue
                
                with self.subTest(unit=wmo_unit):
                    norm_str = WmoUnits.normalize_unit(wmo_unit)
                    try:
                        _ = UnitQuantity(1, norm_str)
                    except Exception as e:
                        self.fail(f'WMO unit parse failure: {e} : unit = "{wmo_unit}" normalized to "{norm_str}"')

    def test_normalize_unit_with_prefixes(self):
        """Test unit normalization with various prefixes"""
        test_units = ['hPa', 'm/s', '˚C', '%']  # Representative sample
        
        for base_unit in test_units:
            for prefix in ['', 'wmoUnit:', 'wmo:', 'unit:']:
                unit_str = f'{prefix}{base_unit}'
                
                with self.subTest(unit_str=unit_str):
                    norm_str = WmoUnits.normalize_unit(unit_str)
                    
                    # Should strip prefixes correctly
                    self.assertFalse(norm_str.startswith(('wmoUnit:', 'wmo:', 'unit:')))
                    
                    # Should be parseable by Pint
                    try:
                        _ = UnitQuantity(1, norm_str)
                    except Exception as e:
                        self.fail(f'Prefixed unit parse failure: {e} : unit = "{unit_str}" normalized to "{norm_str}"')

    def test_canonical_mapping(self):
        """Test that canonical mapping works correctly"""
        test_cases = [
            ('Cel', '˚C'),  # wmoAbbrev2 -> wmoAbbrev
            ('deg', '˚'),   # wmoAbbrev2 -> wmoAbbrev  
            ('hPa/h', 'hPa h^-1'),  # wmoAbbrev2 -> wmoAbbrev
            ('m/s', 'm s^-1'),  # wmoAbbrev2 -> wmoAbbrev
            ('kg/kg', 'kg kg^-1'),  # wmoAbbrev2 -> wmoAbbrev
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_unit_aliases(self):
        """Test that unit aliases work correctly"""
        test_cases = [
            ("'", 'arcminute'),
            ('"', 'arcsecond'),
            ("''", 'arcsecond'),
            ('˚', 'degree'),
            ('Ω', 'ohm'),
            ('cb/12 h', 'cb_per_12h'),
            ('hPa/3 h', 'hPa_per_3h'),
            ('kt/1000 m', 'kt/km'),
            ('m s^-1/1000 m', 'm s^-1/km'),
            ('˚ C/100 m', 'degrees celsius per centimetres'),
            ('m^2/3 s^-1', 'meter_two_thirds_per_second'),
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        test_cases = [
            (None, None),
            ('', ''),
            ('   ', ''),  # Should strip whitespace
            ('unknown_unit', 'unknown_unit'),  # Should pass through unknown units
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled"""
        test_cases = [
            ('  hPa  ', 'hPa'),
            ('\thPa\n', 'hPa'),
            ('unit:  hPa  ', 'hPa'),
            ('wmo:  ˚C  ', 'degree'),  # Should also apply aliases after stripping
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_complex_unit_conversions(self):
        """Test complex units that require special handling"""
        complex_units = [
            'kg m^-2 s^-1',
            'W m^-2 sr^-1',
            'Bq l^-1',
            'J kg^-1',
            'K m s^-1',
            'Pa s^-1',
        ]
        
        for unit in complex_units:
            with self.subTest(unit=unit):
                norm_str = WmoUnits.normalize_unit(unit)
                
                # Should be parseable by Pint
                try:
                    quantity = UnitQuantity(1, norm_str)
                    # Verify it actually created a valid quantity
                    self.assertIsInstance(quantity.magnitude, (int, float))
                except Exception as e:
                    self.fail(f'Complex unit parse failure: {e} : unit = "{unit}" normalized to "{norm_str}"')

    def test_case_sensitivity(self):
        """Test that case variations are handled appropriately"""
        # WMO units are typically case-sensitive, so we test that behavior is preserved
        test_cases = [
            ('hPa', 'hPa'),  # Should preserve case
            ('HPA', 'HPA'),  # Should preserve case even if invalid
            ('celsius', 'celsius'),  # Should preserve case
            ('Pa', 'Pa'),  # Should preserve case
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_prefix_stripping_priority(self):
        """Test that prefix stripping happens before other transformations"""
        test_cases = [
            ('wmoUnit:˚C', 'degree'),  # Should strip prefix then apply alias
            ('unit:Cel', '˚C'),  # Should strip prefix then apply canonical mapping
            ('wmo:%', '%'),  # Should strip prefix and preserve unit
        ]
        
        for input_unit, expected_output in test_cases:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)

    def test_comprehensive_unit_coverage(self):
        """Comprehensive test ensuring all defined units are parseable"""
        failed_units = []
        
        for wmo_unit_def in WmoUnits.UNIT_DEFINITIONS:
            for field in ['wmoAbbrev', 'wmoAbbrev2']:
                wmo_unit = wmo_unit_def.get(field)
                if not wmo_unit or wmo_unit.strip() == '':
                    continue
                    
                norm_str = WmoUnits.normalize_unit(wmo_unit)
                try:
                    UnitQuantity(1, norm_str)
                except Exception:
                    failed_units.append({
                        'original': wmo_unit,
                        'normalized': norm_str,
                        'field': field,
                        'wmo_id': wmo_unit_def.get('wmoId', 'unknown'),
                        'label': wmo_unit_def.get('label', 'unknown')
                    })
        
        if failed_units:
            failure_msg = "Failed to parse units:\n" + "\n".join(
                f"  {unit['original']} -> {unit['normalized']} (ID: {unit['wmo_id']}, Field: {unit['field']}, Label: {unit['label']})"
                for unit in failed_units[:10]  # Limit output for readability
            )
            if len(failed_units) > 10:
                failure_msg += f"\n  ... and {len(failed_units) - 10} more units failed"
            self.fail(failure_msg)

    def test_wmo_id_mapping(self):
        """Test that WMO IDs are properly mapped to canonical abbreviations"""
        # Test some specific WMO ID mappings
        test_cases = []
        
        # Build test cases from the definitions
        for unit_def in WmoUnits.UNIT_DEFINITIONS:
            wmo_id = unit_def.get('wmoId')
            wmo_abbrev = unit_def.get('wmoAbbrev')
            
            if wmo_id and wmo_abbrev and wmo_id != wmo_abbrev:
                test_cases.append((wmo_id, wmo_abbrev))
                
        # Test a representative sample
        sample_test_cases = test_cases[:10] if len(test_cases) > 10 else test_cases
        
        for wmo_id, expected_abbrev in sample_test_cases:
            with self.subTest(wmo_id=wmo_id):
                result = WmoUnits.normalize_unit(wmo_id)
                self.assertEqual(result, expected_abbrev)

    def test_normalization_idempotency(self):
        """Test that normalizing an already normalized unit doesn't change it"""
        sample_units = ['hPa', 'm s^-1', 'degree', 'percent', 'kg m^-2']
        
        for unit in sample_units:
            with self.subTest(unit=unit):
                first_normalize = WmoUnits.normalize_unit(unit)
                second_normalize = WmoUnits.normalize_unit(first_normalize)
                self.assertEqual(first_normalize, second_normalize)

    def test_special_characters_in_units(self):
        """Test handling of special characters that might cause parsing issues"""
        special_units = [
            ('‰', '‰'),  # Per mille symbol
            ('0/00', '‰'),  # Should map to per mille
            ('mol mol^-1', ' mol mol^-1'),  # Note leading space in canonical
            ('pH unit', 'pH unit'),  # Space in unit name
        ]
        
        for input_unit, expected_output in special_units:
            with self.subTest(input_unit=input_unit):
                result = WmoUnits.normalize_unit(input_unit)
                self.assertEqual(result, expected_output)