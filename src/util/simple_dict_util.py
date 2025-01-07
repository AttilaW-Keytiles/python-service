
def dict_getByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None, onlyIfTypeIsAny: type|tuple[type] = None) -> any:
    """
    When you have a dictionary you might want to say "hey give me the entry you find under key 'key1' or 'key2' or 'key3' and if none of them is there give me a default value".
    This method implements exactly this. You simply list your keys to search for. First hit will be returned - no hit then you get back the 'default' value (which is None by default).

    Additionally you can also phrase constraints regarding the expected data type of the entry. So you can say "give me the entry under 'key1' but only if this is a 'str' or 'int'". You
    can do this using the optional `onlyIfTypeIsAny` parameter. They are interpreted using the logical "or" operator.
    """
    if theDict == None or not isinstance(theDict, dict):
        return default
    for key in keys:
        value = theDict.get(key)
        if onlyIfTypeIsAny != None and not isinstance(value, onlyIfTypeIsAny):
            value = None
        if value != None:
            return value
    return default

def dict_getDictByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None) -> any:
    """
    A wrapper around `dict_getByAny()` - it only returns `dict` type entries from the dictionary.
    """
    return dict_getByAny(theDict=theDict, keys=keys, default=default, onlyIfTypeIsAny=dict)

def dict_getArrayByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None) -> any:
    """
    A wrapper around `dict_getByAny()` - it only returns `list` type entries from the dictionary.
    """
    return dict_getByAny(theDict=theDict, keys=keys, default=default, onlyIfTypeIsAny=list)

def dict_getStringByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None) -> any:
    """
    A wrapper around `dict_getByAny()` - it only returns `str` type entries from the dictionary.
    """
    return dict_getByAny(theDict=theDict, keys=keys, default=default, onlyIfTypeIsAny=str)

def dict_getBoolByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None) -> any:
    """
    A wrapper around `dict_getByAny()` - it only returns `bool` type entries from the dictionary.
    """
    return dict_getByAny(theDict=theDict, keys=keys, default=default, onlyIfTypeIsAny=bool)

def dict_getNumberByAny(theDict: dict[any, any], keys: set[any]|tuple[any], default: any = None) -> any:
    """
    A wrapper around `dict_getByAny()` - it only returns `int` or `float` (numeric) type entries from the dictionary.
    """
    return dict_getByAny(theDict=theDict, keys=keys, default=default, onlyIfTypeIsAny=(int,float))