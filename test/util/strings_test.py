from src.util import strings


def test_is_blank():

    # ---- GIVEN
    str = None
    # ---- WHEN-THEN
    assert strings.is_blank(str) == True
    assert strings.is_not_blank(str) == False

    # ---- GIVEN
    str = ""
    # ---- WHEN-THEN
    assert strings.is_blank(str) == True
    assert strings.is_not_blank(str) == False

    # ---- GIVEN
    str = "  \t"
    # ---- WHEN-THEN
    assert strings.is_blank(str) == True
    assert strings.is_not_blank(str) == False

    # ---- GIVEN
    str = "  q "
    # ---- WHEN-THEN
    assert strings.is_blank(str) == False
    assert strings.is_not_blank(str) == True

    # ---- GIVEN
    # we send in invalid input
    str = 65536
    # should raise an error
    errorRaised = None
    # ---- WHEN
    try:
        strings.is_blank(str) == False
    except Exception as e:
        errorRaised = e
    # ---- THEN
    assert errorRaised != None
    assert isinstance(errorRaised, ValueError)