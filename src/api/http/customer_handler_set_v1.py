from fastapi import APIRouter, Request, HTTPException, status, FastAPI
from fastapi.responses import Response
from src.model.api.generated.banking_api_v1 import Customer
from src.model.api.generated.common_v1 import MessageResponse, Problem, ProblemPlaceEnum, CommonErrorCodes, Severity
from src.observability.logging import LoggerFactory, Logger
from src.controller.customer_crud import CustomerCRUDController
from src.util import dependency_validator, ids
from src.model.config.models import ServiceConfig
from src.api.http.base_fastapi_handler_set import BaseFastAPIHandlerSet
from src.context.contexts import FastAPIHttpExecutionContext
from pydantic import BaseModel
from src.api.http.message_response_exception import MessageResponseException
from src.model.error import errors
from util import strings


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


    def _do_attach_to_http_server(self, app: FastAPI) -> None:
        router = APIRouter()
        # hm... this does not work this way... we need a trick!
        #router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI, self.search_customers_proxy, methods=["GET"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI, self.get_customer_proxy, methods=["GET"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI + "/{customerId}", self.get_customer_proxy, methods=["GET"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI + "/{customerId}", self.update_customer_proxy, methods=["PUT"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI + "/{customerId}", self.delete_customer_proxy, methods=["DELETE"])
        router.add_api_route(CustomerHandlerSetV1.BASE_REST_URI, self.create_customer_proxy, methods=["POST"])
        app.include_router(router)


    def _execute_handler_method_wrapper(self, request: Request, method, bodyObject: BaseModel = None):
        """
        Used by _proxy_ methods. It executes the given method "wrapped" - to ensure all boilerplate is done and exceptions handled correctly.

        This way the methods who are running wrapped can really and purely focus on their business logic.
        """
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
            
        except MessageResponseException as exc:
            # just simply throw it
            raise exc
        except Exception as exc:
            msgRespException = MessageResponseException.from_exception(exc=exc, cntx=cntx)
            # throw it the way we set the cause too
            raise msgRespException from exc
        finally:
            tookMillis = cntx.get_ellapsed_millis()
            self._LOG.debug("Req-Resp completed - took %s millis", tookMillis, **labels)

        return resp


    # attilaw: crap! mapping does not work in Router - needed a trick :-P
    # def search_customers_proxy(self, request: Request):
    #     return self._execute_handler_method_wrapper(request=request, method=self.get_customer)

    def search_customers(self, cntx: FastAPIHttpExecutionContext) -> Response:

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Sorry... not implemented yet... :-()"
        resp = self._get_prepared_http_response(status_code = status.HTTP_501_NOT_IMPLEMENTED, bodyModel = msgResp, cntx = cntx)
        return resp


    def get_customer_proxy(self, request: Request):
        customer_id: str = request.path_params.get("customerId")
        if strings.is_blank(customer_id):
            return self._execute_handler_method_wrapper(request=request, method=self.search_customers)
        else:
            return self._execute_handler_method_wrapper(request=request, method=self.get_customer)


    def get_customer(self, cntx: FastAPIHttpExecutionContext) -> Response:
        customer_id: str = cntx.http_request.path_params.get("customerId")
        customer = self._customer_crud_contoller.get(customer_id=customer_id, cntx=cntx)

        if customer == None:
            raise self._get_customer404_error(cntx=cntx)

        resp: Response = self._get_prepared_http_response(bodyModel=customer, cntx=cntx)
        return resp
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Customer - just need to declare it as param. Convenient!
    def create_customer_proxy(self, request: Request, customer: Customer):
        resp = self._execute_handler_method_wrapper(request=request, method=self.create_customer, bodyObject=customer)
        return resp


    def create_customer(self, cntx: FastAPIHttpExecutionContext, bodyObject: Customer):

        if bodyObject.id == None or bodyObject.id == "":
            bodyObject.id = ids.generate_uuid()

        if bodyObject.version != None and bodyObject.version != 0:
            raise MessageResponseException(
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
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Customer - just need to declare it as param. Convenient!
    def update_customer_proxy(self, request: Request, customer: Customer):
        resp = self._execute_handler_method_wrapper(request=request, method=self.update_customer, bodyObject=customer)
        return resp


    def update_customer(self, cntx: FastAPIHttpExecutionContext, bodyObject: Customer):

        customer_id: str = cntx.http_request.path_params.get("customerId")

        # check the id!
        if bodyObject.id == None:
            bodyObject.id = customer_id
        else:
            if customer_id != bodyObject.id:
                # Not good!
                raise MessageResponseException(
                    cntx = cntx,
                    status_code = status.HTTP_400_BAD_REQUEST,
                    #detail = CustomerAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                    problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/id", errorCodes=[CommonErrorCodes.data_contradictingRequest], message="The 'id' you provided in the body does not match with the {customerId} you provided on the URL. They must match."))

        # version must be present!
        if bodyObject.version == None:
            # Not good!
            raise MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                #detail = CustomerAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/version", errorCodes=[CommonErrorCodes.information_missing], message="In updates you must provide the 'version' of the resource in the body - this should be the same as you got back when you queried the resource!"))

        try:
            self._customer_crud_contoller.update(customer_data = bodyObject)
        except errors.ResourceNotFoundError as exc:
            raise self._get_customer404_error(cntx=cntx)
        
        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Customer updated"
        resp = self._get_prepared_http_response(status_code = status.HTTP_200_OK, bodyModel = msgResp, cntx = cntx)
        return resp



    # helper method to DRY
    def _get_customer404_error(self, cntx: FastAPIHttpExecutionContext) -> MessageResponseException:
        return MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Customer does not exist",
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.urlParam, placeName="{customerId}", errorCodes=[CommonErrorCodes.requestParameter_invalid], message="invalid customerId"))


    def delete_customer_proxy(self, request: Request):
        return self._execute_handler_method_wrapper(request=request, method=self.delete_customer)


    def delete_customer(self, cntx: FastAPIHttpExecutionContext) -> Response:
        customer_id: str = cntx.http_request.path_params.get("customerId")

        try:
            self._customer_crud_contoller.delete(customer_id = customer_id)
        except errors.ResourceNotFoundError as exc:
            raise self._get_customer404_error(cntx=cntx)
        
        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Customer deleted"
        resp = self._get_prepared_http_response(status_code = status.HTTP_200_OK, bodyModel = msgResp, cntx = cntx)
        return resp
