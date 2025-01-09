from fastapi import APIRouter, Request, status, FastAPI
from fastapi.responses import Response
from src.model.api.generated.banking_api_v1 import Transfer
from src.model.api.generated.common_v1 import MessageResponse, Problem, ProblemPlaceEnum, CommonErrorCodes, Severity
from src.observability.logging import LoggerFactory, Logger
from src.controller.transfer_crud import TransferCRUDController
from src.util import dependency_validator
from src.model.config.models import ServiceConfig
from src.api.http.base_fastapi_handler_set import BaseFastAPIHandlerSet
from src.context.contexts import FastAPIHttpExecutionContext
from pydantic import BaseModel
from src.api.http.message_response_exception import MessageResponseException
from src.model.error import errors
from util import strings


class TransferHandlerSetV1(BaseFastAPIHandlerSet):
    """
    This handler class is bound to FastAPI HTTP server to deal with Transfer related endpoints.
    """

    BASE_URI = "/api/v1/transfers"
    BASE_REST_URI = BASE_URI + "/rest"

    def __init__(self, transfer_crud_contoller: TransferCRUDController, service_config: ServiceConfig):
        super().__init__(service_config=service_config, logger_to_use=LoggerFactory.getLogger("service.api.http.TransferHandler"))

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='transfer_crud_contoller', paramValueToCheck=transfer_crud_contoller, acceptedTypes=(TransferCRUDController), loggerToUse=self._LOG)

        self._transfer_crud_contoller = transfer_crud_contoller
        """Our controller - HTTP operations are mapped into method invocations on it"""


    def _do_attach_to_http_server(self, app: FastAPI) -> None:
        router = APIRouter()
        # hm... this does not work this way... we need a trick!
        #router.add_api_route(TransferHandlerSetV1.BASE_REST_URI, self.search_transfers_proxy, methods=["GET"])
        router.add_api_route(TransferHandlerSetV1.BASE_REST_URI, self.get_transfer_proxy, methods=["GET"])
        router.add_api_route(TransferHandlerSetV1.BASE_REST_URI + "/{transferId}", self.get_transfer_proxy, methods=["GET"])
        router.add_api_route(TransferHandlerSetV1.BASE_REST_URI, self.create_transfer_proxy, methods=["POST"])
        app.include_router(router)


    # attilaw: crap! mapping does not work in Router - needed a trick :-P
    # def search_transfers_proxy(self, request: Request):
    #     return self._execute_handler_method_wrapper(request=request, method=self.get_transfer)

    def search_transfers(self, cntx: FastAPIHttpExecutionContext) -> Response:

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Sorry... not implemented yet... :-()"
        resp = self._get_prepared_http_response(status_code = status.HTTP_501_NOT_IMPLEMENTED, bodyModel = msgResp, cntx = cntx)
        return resp


    def get_transfer_proxy(self, request: Request):
        transfer_id: str = request.path_params.get("transferId")
        if strings.is_blank(transfer_id):
            return self._execute_handler_method_wrapper(request=request, method=self.search_transfers)
        else:
            return self._execute_handler_method_wrapper(request=request, method=self.get_transfer)


    def get_transfer(self, cntx: FastAPIHttpExecutionContext) -> Response:
        transfer_id: str = cntx.http_request.path_params.get("transferId")
        transfer = self._transfer_crud_contoller.get(transfer_id=transfer_id, cntx=cntx)

        if transfer == None:
            raise self._get_transfer404_error(cntx=cntx)

        resp: Response = self._get_prepared_http_response(bodyModel=transfer, cntx=cntx)
        return resp
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Transfer - just need to declare it as param. Convenient!
    def create_transfer_proxy(self, request: Request, transfer: Transfer):
        resp = self._execute_handler_method_wrapper(request=request, method=self.create_transfer, bodyObject=transfer)
        return resp


    def create_transfer(self, cntx: FastAPIHttpExecutionContext, bodyObject: Transfer):

        # we take back the id
        self._transfer_crud_contoller.create(transfer_data=bodyObject, cntx=cntx)

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Transfer created"
        resp = self._get_prepared_http_response(status_code = status.HTTP_201_CREATED, bodyModel = msgResp, cntx = cntx)
        return resp
    


    # helper method to DRY
    def _get_transfer404_error(self, cntx: FastAPIHttpExecutionContext) -> MessageResponseException:
        return MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Transfer does not exist",
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.urlParam, placeName="{transferId}", errorCodes=[CommonErrorCodes.requestParameter_invalid], message="invalid transferId"))

