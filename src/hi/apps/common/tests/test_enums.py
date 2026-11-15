import logging

from django.test import SimpleTestCase

from hi.apps.common.enums import LabeledEnum

logging.disable(logging.CRITICAL)


class ColorEnum(LabeledEnum):
    RED = ('Red', '')
    GREEN = ('Green', '')
    DARK_BLUE = ('Dark Blue', '')

    @classmethod
    def default(cls):
        return cls.GREEN


class OtherEnum(LabeledEnum):
    RED = ('Other Red', '')


class TestLabeledEnumFromName(SimpleTestCase):

    def test_matches_case_insensitively_and_ignores_surrounding_whitespace(self):
        for name in [ 'dark_blue', 'DARK_BLUE', 'Dark_Blue', '  dark_blue\n' ]:
            with self.subTest( name = name ):
                self.assertIs( ColorEnum.from_name( name ), ColorEnum.DARK_BLUE )

    def test_none_sentinel_returns_none(self):
        self.assertIsNone( ColorEnum.from_name( '_none_' ) )

    def test_empty_or_missing_name_raises(self):
        for name in [ '', None ]:
            with self.subTest( name = name ):
                with self.assertRaises( ValueError ):
                    ColorEnum.from_name( name )

    def test_unknown_name_raises(self):
        with self.assertRaises( ValueError ):
            ColorEnum.from_name( 'purple' )

    def test_from_name_safe_falls_back_to_default(self):
        self.assertIs( ColorEnum.from_name_safe( 'purple' ), ColorEnum.GREEN )

    def test_same_member_name_resolves_within_each_enum_class(self):
        # Lookup tables are cached per class and must not cross over.
        self.assertIs( ColorEnum.from_name( 'red' ), ColorEnum.RED )
        self.assertIs( OtherEnum.from_name( 'red' ), OtherEnum.RED )
