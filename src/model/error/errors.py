"""
In this module we declare a few common error types we can use Service-wise for more sophisticated error handling.
"""

class ServiceRuntimeError(RuntimeError):
    """
    This error (exception) can carry some minimalistic named information: human and machine readable stuff.

    `message` is the first parameter as it is strongly recommended to add one - at least humans can understand (from logs?).
    However `error_codes` is also very handy - for machine readable situations. Still comes 2nd as can be optional.
    **Please note:** this error can store not just one but multiple error codes! This is not a coincidence...
    """
    
    def __init__(self, message: str, error_codes: str|set[str]|list[str] = None, *args, **kwargs):
        super().__init__(message, error_codes, *args, **kwargs)
        self.message = message
        """Human readable message"""
        self.error_codes = error_codes
        """
        Set of machine readable error codes - related to the problem. See the convenience hasError() method!
        (yes, they are strings and not numerical! for maximum usability and human readability in logs)
        """
        # let's make sure the error codes are converted to set[str]! We can not throw another violation exception from an exception creation right? :-P
        if self.error_codes == None:
            self.error_codes = set()
        if isinstance(self.error_codes, str):
            # lets convert single error code into one-element set
            self.error_codes = {self.error_codes}
        if isinstance(self.error_codes, list):
            # lets convert to set
            self.error_codes = set(self.error_codes)
        # TODO what if someone has sent in let's say {5, 6} ? so not strings but integers ...

    def has_error(self, error_code: str) -> bool:
        """Tells you if the given error code is associated with this error or not"""
        return error_code in self.error_codes
    

class IllegalStateError(ServiceRuntimeError):
    pass


class ConstraintViolationError(ServiceRuntimeError):
    """
    Controller and Persistence (DAO) layers can throw this error to describe they ran into a "conflict" of something.

    E.g. someone tries to create a business object however the ID is already taken... So we have a "conflict".

    This class provides a few pre-populated error codes - for typical situations
    """

    ERRCODE_ID_ALREADY_TAKEN = "id_already_taken"
    """Use this error code if you have a resource conflicting PrimaryKey or ID"""


class OptimisticLockingError(ConstraintViolationError):
    """
    It is a special case of ConstraintViolation. But some extra info can come handy... So this one can be used in situations where we implement "optimistic locking" based on versioned resources
    """

    ERRCODE_VERSION_CONFLICT = "resource_version_conflict"
    """Use this error code if you have a resource conflicting assumed vs real versions"""

    def __init__(self, message, error_codes: str|set[str]|list[str], assumed_version: int, actual_version: int, *args, **kwargs):
        super().__init__(message, error_codes, message, *args, **kwargs)
        self.assumed_version = assumed_version
        """Tells the caller what he passed as 'assumed' resource vesion"""
        self.actual_version = actual_version
        """Tells the caller that in contrast with his 'assumed' resource vesion it is actually this version now"""


class ResourceNotFoundError(ServiceRuntimeError):
    """
    Controller and Persistence (DAO) layers can throw this error to describe they could not find a record/resource which was requested.

    E.g. someone tries to query a business object belongs to the ID but it does not exist.

    This class provides a few pre-populated error codes - for typical situations
    """