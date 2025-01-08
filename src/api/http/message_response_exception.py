from fastapi import status, HTTPException
from src.context.contexts import FastAPIHttpExecutionContext
from src.model.api.generated.common_v1 import MessageResponse, Problem, ProblemPlaceEnum, CommonErrorCodes, Severity
from src.model.error import errors

class MessageResponseException(HTTPException):
    """
    This special HTTPException - which we want to to be able to ditinguish from pure HTTPExceptions however content is the same.
    Why do we want this then?
    Because we want to customize FastAPI error handling and register and exception handler dealing with these ones.
    Why?
    Because in the API contract we promise meaningful MessageResponses in case of error scenarios like 4xx, 5xx.

    So to fulfill this when the service endpoint handlers are detecting a problem and want to raise 4xx, 5xx errors they can nicely
    assemble a MessageResponseException and throw that. That's it. The attached exception handler will take care of the conversion then.

    On the top of this please note this class comes with a static factory method `from_Exception()`! This guy brings even more possibilities into the game
    but read the method commet ;-)

    This helps to make business logic of handlers much much slimmer by eliminating lots of boilerplate.
    """

    DETAILMSG_GENERIC_OP_FAILURE = "Operation failed - there is at least one error! See /problems entry for more details!"

    @staticmethod
    def from_exception(exc: Exception, cntx: FastAPIHttpExecutionContext = None):
        """
        This static method converts any exception into a MessageResponseException - might make life easier...
        It can recognize our own `~src.model.error.errors` package exceptions too and do a best effort in the conversion.
        """

        if isinstance(exc, MessageResponseException):
            # piece of cake!
            return exc

        msgAddition = "\nMore details you might find in the log!"
        if cntx != None:
            msgAddition += " Search for transactionId '"+cntx.transaction_id+"'"

        if isinstance(exc, errors.ConstraintViolationError):
            # should result in 409 by default
            handlerExc = MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_409_CONFLICT,
                # the message of these type exceptions should be safe to be returned for users
                detail = exc.message + msgAddition,
                problems = MessageResponseException._convert_exception_errorcodes_to_problems(error_codes = exc.error_codes, originalExc = exc)
            )
            return handlerExc

        if isinstance(exc, errors.ResourceNotFoundError):
            # should result in 404 by default
            handlerExc = MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_404_NOT_FOUND,
                # the message of these type exceptions should be safe to be returned for users
                detail = exc.message + msgAddition,
                problems = MessageResponseException._convert_exception_errorcodes_to_problems(error_codes = exc.error_codes, originalExc = exc)
            )
            return handlerExc

        if isinstance(exc, errors.ValidationError):
            # should result in 400 by default
            handlerExc = MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                # the message of these type exceptions should be safe to be returned for users
                detail = exc.message + msgAddition,
                problems = MessageResponseException._convert_exception_errorcodes_to_problems(error_codes = exc.error_codes, originalExc = exc)
            )
            return handlerExc


        # Careful! We can not anyhow expose any sensitive detail of the exception back to the response!
        # That info belongs to logs... so here is a nice default - just in case
        safeDetail = "Something went wrong... " + msgAddition

        problems: list[Problem] = list()
        if isinstance(exc, errors.ServiceRuntimeError):
            problems = MessageResponseException._convert_exception_errorcodes_to_problems(error_codes = exc.error_codes, originalExc = exc)
        if len(problems) == 0:
            problems.append(Problem(severity=Severity.error, errorCodes=[CommonErrorCodes.processing_failed_internally], message = type(exc).__name__ + " was raised"))

        capiExc = MessageResponseException(
            cntx = cntx,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = safeDetail,
            problems = problems
        )
        return capiExc
    
    
    @staticmethod
    def _convert_exception_errorcodes_to_problems(error_codes: set[str], originalExc: errors.ServiceRuntimeError) -> list[Problem]:
        problems: list[Problem] = list()
        unrecognized_codes: list[str] = list()
        for error_code in error_codes:
            match error_code:
                case errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN:
                    problems.append(
                        Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.id_already_used], message = "The ID you tried to assign is already taken")
                    )
                case errors.OptimisticLockingError.ERRCODE_VERSION_CONFLICT:
                    # time to translate problems
                    msg = "Race condition detected - server has different version"
                    if isinstance(originalExc, errors.OptimisticLockingError) and originalExc.actual_version != None and originalExc.assumed_version != None:
                        # we can create better human message
                        msg = f"Race condition detected - your assumption was that resource version is {originalExc.assumed_version} but in reality server resource has version {originalExc.actual_version}"
                    problems.append(
                        Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.resourceVersion_mismatch], message = msg)
                    )
                case errors.ValidationError.ERRCODE_MISSING_MANDATORY:
                    problem: Problem = Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.information_missing], message = "Mandatory information was not provided")
                    if isinstance(originalExc, errors.ValidationError) and originalExc.place_name != None:
                        problem.placeName = originalExc.place_name
                    problems.append(problem)
                case errors.ValidationError.ERRCODE_WRONG_DATATYPE:
                    problem: Problem = Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.information_wrongFormat], message = "Wrong type of data was provided")
                    if isinstance(originalExc, errors.ValidationError) and originalExc.place_name != None:
                        problem.placeName = originalExc.place_name
                    problems.append(problem)
                case errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED:
                    problem: Problem = Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.information_pointless], message = "This data was not expected to be provided")
                    if isinstance(originalExc, errors.ValidationError) and originalExc.place_name != None:
                        problem.placeName = originalExc.place_name
                    problems.append(problem)
                case errors.ValidationError.ERRCODE_INVALID_VALUE:
                    problem: Problem = Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.information_invalid], message = "Provided data is not valid")
                    if isinstance(originalExc, errors.ValidationError) and originalExc.place_name != None:
                        problem.placeName = originalExc.place_name
                    problems.append(problem)
                case errors.ValidationError.ERRCODE_READONLY_VALUE_CHANGED:
                    problem: Problem = Problem(severity = Severity.error, errorCodes=[CommonErrorCodes.information_readonly], message = "Provided data is different from existing however existing data is read-only")
                    if isinstance(originalExc, errors.ValidationError) and originalExc.place_name != None:
                        problem.placeName = originalExc.place_name
                    problems.append(problem)
                case _:
                    unrecognized_codes.append(error_code)
        if len(unrecognized_codes) > 0:
            # let's add all others just simply - here we can not fulfill our contract promise but fine, do not swallow what we have
            problems.append(
                Problem(severity = Severity.error, errorCodes=unrecognized_codes, message = "These error codes are not part of the API contract but was provided by the application layer")
            )
    
        return problems


    def __init__(self, status_code, detail = None, headers = None, problems: Problem|list[Problem] = None, cntx: FastAPIHttpExecutionContext = None):
        # OK let's save some lazy crap... if one does not provide details...
        if detail == None:
            self.detail = MessageResponseException.DETAILMSG_GENERIC_OP_FAILURE
        # now we can init our superclass
        super().__init__(status_code, detail, headers)

        if problems != None and isinstance(problems, Problem):
            # we convert singe problem into a list
            problems = [problems]
        self.problems = problems
        self.cntx = cntx


    def __str__(self):
        s = type(self).__name__ + f"[status: {self.status_code}, message: {self.detail}, problems: {self.problems}"
        cause = self.__cause__
        if cause:
            s += f", cause: {cause}"
        s += "]"
        return s


