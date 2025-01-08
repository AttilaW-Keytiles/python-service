from src.util import preconditions
from enum import Enum

class AccountStatus(Enum):
    active = 'active'
    disabled = 'disabled'
    closed = 'closed'

def test_check_enum_value():

    # ---- WHEN

    thrownError = None
    try:
        preconditions.check_enum_value("active", AccountStatus, "just a message if not member...")
        preconditions.check_enum_value("disabled", AccountStatus, "just a message if not member...")
        preconditions.check_enum_value("closed", AccountStatus, "just a message if not member...")
    except Exception as e:
        thrownError = e

    # ---- THEN

    # we should not have any errors thrown
    assert thrownError is None

    # ---- WHEN

    valueNotPresent = "itsnotthere"
    thrownError = None
    try:
        preconditions.check_enum_value(valueNotPresent, AccountStatus, "hey buddy the value '{}' is not part of the enum {}", valueNotPresent, type(AccountStatus))
    except Exception as e:
        thrownError = e

    # ---- THEN

    # we should not have any errors thrown
    assert thrownError is not None
    assert "hey buddy the value 'itsnotthere' is not part of the enum <class 'enum.EnumType'>" == str(thrownError)
