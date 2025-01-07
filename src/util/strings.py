
def isBlank(s: str) -> bool:
    """Returns TRUE if string is either None or only has white spaces"""
    return not s or not s.strip()

def isNotBlank(s: str) -> bool:
    """Returns TRUE if string is not None and has at least one character other than whitespace"""
    return not isBlank(s)