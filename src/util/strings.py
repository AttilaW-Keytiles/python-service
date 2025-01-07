from src.util import preconditions

def is_blank(s: str) -> bool:
    """Returns TRUE if string is either None or only has white spaces"""
    preconditions.check_argument(s == None or isinstance(s, str), "input parameter must be string - you passed {}", type(s))
    return not s or not s.strip()

def is_not_blank(s: str) -> bool:
    """Returns TRUE if string is not None and has at least one character other than whitespace"""
    return not is_blank(s)