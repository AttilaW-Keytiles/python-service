
class ServiceRuntimeError(RuntimeError):
    """
    This error (exception) can carry some minimalistic named information

    `message` is the first parameter as it is strongly recommended to add one - at least humans can understand (from logs?).
    However `error_code` is also very handy - for machine readable situations. Still comes 2nd as can be optional.
    
    """
    
    def __init__(self, message: str, error_code: str, *args, **kwargs):
        super().__init__(message, error_code, *args, **kwargs)
        self.message = message
        """Human readable message"""
        self.error_code = error_code
        """The machine readable error code (yes, its a string not int for maximum usability without meaningless integers and enforced enums)"""

class IllegalStateError(ServiceRuntimeError):
    pass

class OptimisticLockingError(ServiceRuntimeError):
    """Can be used in situations where we implement "optimistic locking" based on versioned resources"""

    def __init__(self, message, error_code, assumed_version: int, actual_version: int, *args, **kwargs):
        super().__init__(message, error_code, message, *args, **kwargs)
        self.assumed_version = assumed_version
        """Tells the caller what he passed as 'assumed' resource vesion"""
        self.actual_version = actual_version
        """Tells the caller that in contrast with his 'assumed' resource vesion it is actually this version now"""
