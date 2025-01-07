from src.observability.logging import Logger

def ensureGivenAndTypeMatching(targetInstance: object, paramValueToCheck: any, paramName: str, acceptedTypes: type|tuple[type], loggerToUse: Logger = None) -> None:
    """
    Helper method to validate a given dependency - related to Dependency Injection. This method will raise an error if the checked dependency
    is `None` (not given) or even if given does not have one of the listed types in `acceptedTypes`.
    Using this method bring standardized errors / behavior and eliminate related boiler plate code from the point of validation.

    Params:
     * `targetInstance`: here you pass the obj reference where you are doing the validation right now (typically `self` you will pass here)
     * `paramValueToCheck`: just pass over the dependency you want to check
     * `paramName`: the name of the param in your method signature which carries the dependency - it used for error text generation
     * `acceptedTypes`: provide the type(s) you want to accept the dependency has
     * `loggerToUse`: makes sense to pass your Logger if you have there one around - if you do then an error will be logged immediately
    """
    if paramValueToCheck == None:
        err = f"Failed to instantiate {targetInstance.__class__} due to dependency injection issue! '{paramName}' can not be None! You must provide it."
        if loggerToUse != None:
            loggerToUse.error(err)
        raise ValueError(err)
    if not isinstance(paramValueToCheck, acceptedTypes):
        # create err message
        acceptedTypeNames = _getAcceptedTypeNameList(acceptedTypes=acceptedTypes)
        err = f"Failed to instantiate {targetInstance.__class__} due to dependency injection issue! '{paramName}' must be one of types {acceptedTypeNames} but you provided type '{type(paramValueToCheck)}'!"
        if loggerToUse != None:
            loggerToUse.error(err)
        raise ValueError(err)

def ensureNoneOrTypeMatching(targetInstance: object, paramValueToCheck: any, paramName: str, acceptedTypes: type|tuple[type], loggerToUse: Logger = None) -> None:
    """
    Helper method to validate a given dependency - related to Dependency Injection. This method will raise an error if the checked dependency
    is not `None` (given) and does not have one of the listed types in `acceptedTypes`.
    Using this method bring standardized errors / behavior and eliminate related boiler plate code from the point of validation.

    Params:
     * `targetInstance`: here you pass the obj reference where you are doing the validation right now (typically `self` you will pass here)
     * `paramValueToCheck`: just pass over the dependency you want to check
     * `paramName`: the name of the param in your method signature which carries the dependency - it used for error text generation
     * `acceptedTypes`: provide the type(s) you want to accept the dependency has
     * `loggerToUse`: makes sense to pass your Logger if you have there one around - if you do then an error will be logged immediately
    """
    if paramValueToCheck != None and not isinstance(paramValueToCheck, acceptedTypes):
        # create err message
        acceptedTypeNames = _getAcceptedTypeNameList(acceptedTypes=acceptedTypes)
        err = f"Failed to instantiate {targetInstance.__class__} due to dependency injection issue! '{paramName}' must be one of types {acceptedTypeNames} but you provided type '{type(paramValueToCheck)}'!"
        if loggerToUse != None:
            loggerToUse.error(err)
        raise ValueError(err)


def _getAcceptedTypeNameList(acceptedTypes: type|tuple[type]) -> list[str]:
    # let's assemble the readable list of accepted types
    acceptedTypeNames: list[str] = list()
    if isinstance(acceptedTypes, type):
        acceptedTypeNames.append(acceptedTypes.__qualname__)
    else:
        for t in acceptedTypes:
            acceptedTypeNames.append(t.__qualname__)
    return acceptedTypeNames
