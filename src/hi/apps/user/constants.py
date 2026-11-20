from hi.apps.common.keypad_spec import KeypadSpec


class UserConstants:

    # Single definition of the sign-in magic code: the generator draws from
    # this alphabet and length, and the keypad renders it.
    MAGIC_CODE_KEYPAD = KeypadSpec(
        alphabet = 'abcdefhkpqrstwxy',
        length = 6,
        columns = 4,
        masked = False,
        case_sensitive = False,
    )
