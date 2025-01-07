from fastapi import APIRouter, Request, HTTPException, status, FastAPI
from fastapi.responses import Response
from src.model.api.generated.banking_api_v1 import Customer
from src.model.api.generated.common_v1 import MessageResponse, Problem, ProblemPlaceEnum, CommonErrorCodes, Severity
from src.observability.logging import LoggerFactory, Logger
from src.controller.customer_crud import CustomerCRUDController
from src.util import dependency_validator, ids
from src.config.models import ServiceConfig
from src.api.http.base_fastapi_handler_set import BaseFastAPIHandlerSet
from src.context.contexts import FastAPIHttpExecutionContext
from src.error import errors
from pydantic import BaseModel


class CustomerAPIException(HTTPException):
    """
    Methods in this handler can raise this exception in case of issue. The contract says we return a MessageResponse in these cases.
    This is ensured by a registered exception handler - customer_api_exception_handler() - bound to this type of exception.
    """

    DETAILMSG_GENERIC_OP_FAILURE = "Operation failed - there is at least one error! See /problems entry for more details!"

    def __init__(self, status_code, detail = None, headers = None, problems: Problem|list[Problem] = None, cntx: FastAPIHttpExecutionContext = None):
        # OK let's save some lazy crap... if one does not provide details...
        if detail == None:
            self.detail = CustomerAPIException.DETAILMSG_GENERIC_OP_FAILURE
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


class CustomerHandlerSetV1(BaseFastAPIHandlerSet):
    """
    This handler class is bound to FastAPI HTTP server to deal with Customer related endpoints.

    After class is instantiated 
    """

    BASE_URI = "/api/v1/customer"
    BASE_REST_URI = BASE_URI + "/rest"

    def __init__(self, customer_crud_contoller: CustomerCRUDController, service_config: ServiceConfig):
        super().__init__(service_config=service_config, logger_to_use=LoggerFactory.getLogger("service.api.http.CustomerHandler"))

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='customer_crud_contoller', paramValueToCheck=customer_crud_contoller, acceptedTypes=(CustomerCRUDController), loggerToUse=self._LOG)

        self._customer_crud_contoller = customer_crud_contoller
        """Our controller - HTTP operations are mapped into method invocations on it"""

    # Internal  helper - converts any exception into CustomerAPIException
    def _exception_to_CustomerAPIException(self, exc: Exception, cntx: FastAPIHttpExecutionContext = None) -> CustomerAPIException:
        """
        This static method converts another exception into a CustomerAPIException so we can capture it and send appropriate MessageResponse according to contract
        """

        if isinstance(exc, CustomerAPIException):
            # piece of cake!
            return exc

        # Careful! We can not anyhow expose any detail of the exception back to the response!
        # That info belongs to logs...

        detail = "Something went wrong... More details you might find in the log!"
        if cntx != None:
            detail += " Search for transactionId '"+cntx.transaction_id+"'"

        capiExc = CustomerAPIException(
            cntx = cntx,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = detail,
            problems = Problem(severity=Severity.error, errorCodes=[CommonErrorCodes.processing_failed_internally], message = type(exc).__name__ + " was raised")
        )
        return capiExc


    def _do_attach_to_http_server(self, app: FastAPI) -> None:
        router = APIRouter()
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI + "/{customerId}", self.get_customer_proxy, methods=["GET"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI, self.create_customer_proxy, methods=["POST"])
        app.include_router(router)
        app.add_exception_handler(CustomerAPIException, self.customer_api_exception_handler)


    # This handler is registered to deal with CustomerAPIException - which we convert into MessageResponse
    def customer_api_exception_handler(self, request: Request, exc: CustomerAPIException):
        labels = exc.cntx.get_minimmal_info_for_log() if exc.cntx != None else dict()
        # let's log the captured exception!
        self._LOG.error("request failed! error was: %s\ntraceback: %s", exc, exc.__traceback__, **labels)

        # we assemble the MessageResponse which will become the body
        msgResp = self._get_prepared_MessageResponse(cntx = exc.cntx)
        msgResp.message = exc.detail
        msgResp.problems = exc.problems
        # and now let's create the http response
        resp = self._get_prepared_http_response(status_code=exc.status_code, headers=exc.headers, cntx=exc.cntx, bodyModel=msgResp)
        return resp


    def handler_methods_execution_wrapper(self, request: Request, method, bodyObject: BaseModel = None):
        # as firs step - we need a context derived from the inbound request
        cntx: FastAPIHttpExecutionContext = self._create_execution_context(http_request=request)
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()

        self._log_inbound_request(http_request=request, cntx=cntx)

        resp: Response = None

        # things could go wrong... so let's wrap it!
        try:
            if bodyObject == None:
                resp = method(cntx)
            else:
                resp = method(cntx, bodyObject)
            
        except CustomerAPIException as exc:
            # just simply throw it
            raise exc
        except Exception as exc:
            capiException = self._exception_to_CustomerAPIException(exc=exc, cntx=cntx)
            # throw it the way we set the cause too
            raise capiException from exc
        finally:
            tookMillis = cntx.get_ellapsed_millis()
            self._LOG.debug("Req-Resp completed - took %s millis", tookMillis, **labels)

        return resp


    def get_customer_proxy(self, request: Request):
        return self.handler_methods_execution_wrapper(request=request, method=self.get_customer)


    def get_customer(self, cntx: FastAPIHttpExecutionContext) -> Response:

        customer_id: str = cntx.http_request.path_params.get("customerId")
        customer = self._customer_crud_contoller.get(customer_id=customer_id, cntx=cntx)

        if customer == None:
            raise CustomerAPIException(
                cntx = cntx,
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Customer does not exist",
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.urlParam, placeName="{customerId}", errorCodes=[CommonErrorCodes.requestParameter_invalid], message="invalid customerId"))

        resp: Response = self._get_prepared_http_response(bodyModel=customer, cntx=cntx)
        return resp
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Customer - just need to declare it as param. Convenient!
    def create_customer_proxy(self, request: Request, customer: Customer):
        resp = self.handler_methods_execution_wrapper(request=request, method=self.create_customer, bodyObject=customer)
        return resp


    def create_customer(self, cntx: FastAPIHttpExecutionContext, bodyObject: Customer):

        if bodyObject.id == None or bodyObject.id == "":
            bodyObject.id = ids.generate_uuid()

        if bodyObject.version != None and bodyObject.version != 0:
            raise CustomerAPIException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                #detail = CustomerAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/version", errorCodes=[CommonErrorCodes.resourceVersion_mismatch], message="If you provide 'version' of the Customer resource during creation then you need to set it to 0 - or leave it out entirely."))
        # let's set version to 1
        bodyObject.version = 1

        # we take back the id
        bodyObject.id = self._customer_crud_contoller.create(customer_data=bodyObject, cntx=cntx)

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Customer created"
        resp = self._get_prepared_http_response(status_code = status.HTTP_201_CREATED, bodyModel = msgResp, cntx = cntx, headers={"x-customer-id": bodyObject.id})
        return resp
    

    def update_customer(self, cntx: FastAPIHttpExecutionContext, bodyObject: Customer):

        customer_id: str = cntx.http_request.path_params.get("customerId")

        if bodyObject.version == None:
            raise CustomerAPIException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                #detail = CustomerAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/version", errorCodes=[CommonErrorCodes.resourceVersion_missing, CommonErrorCodes.information_missing], message="You must provide the 'version' of the Customer resource - as you know it from your GET request when you queried the Customer earlier."))
