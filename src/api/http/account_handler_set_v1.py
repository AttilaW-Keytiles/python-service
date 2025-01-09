from fastapi import APIRouter, Request, HTTPException, status, FastAPI
from fastapi.responses import Response
from src.model.api.generated.banking_api_v1 import Account
from src.model.api.generated.common_v1 import MessageResponse, Problem, ProblemPlaceEnum, CommonErrorCodes, Severity
from src.observability.logging import LoggerFactory, Logger
from src.controller.account_crud import AccountCRUDController
from src.util import dependency_validator, ids
from src.model.config.models import ServiceConfig
from src.api.http.base_fastapi_handler_set import BaseFastAPIHandlerSet
from src.context.contexts import FastAPIHttpExecutionContext
from pydantic import BaseModel
from src.api.http.message_response_exception import MessageResponseException
from src.model.error import errors
from util import strings


class AccountHandlerSetV1(BaseFastAPIHandlerSet):
    """
    This handler class is bound to FastAPI HTTP server to deal with Account related endpoints.
    """

    BASE_URI = "/api/v1/accounts"
    BASE_REST_URI = BASE_URI + "/rest"
    BASE_OPERATIONS_URI = BASE_URI + "/operation"

    def __init__(self, account_crud_contoller: AccountCRUDController, service_config: ServiceConfig):
        super().__init__(service_config=service_config, logger_to_use=LoggerFactory.getLogger("service.api.http.AccountHandler"))

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='account_crud_contoller', paramValueToCheck=account_crud_contoller, acceptedTypes=(AccountCRUDController), loggerToUse=self._LOG)

        self._account_crud_contoller = account_crud_contoller
        """Our controller - HTTP operations are mapped into method invocations on it"""


    def _do_attach_to_http_server(self, app: FastAPI) -> None:
        router = APIRouter()
        # hm... this does not work this way... we need a trick!
        #router.add_api_route(AccountHandlerSetV1.BASE_REST_URI, self.search_accounts_proxy, methods=["GET"])
        router.add_api_route(AccountHandlerSetV1.BASE_REST_URI, self.get_account_proxy, methods=["GET"])
        router.add_api_route(AccountHandlerSetV1.BASE_REST_URI + "/{accountId}", self.get_account_proxy, methods=["GET"])
        router.add_api_route(AccountHandlerSetV1.BASE_REST_URI + "/{accountId}", self.update_account_proxy, methods=["PUT"])
        router.add_api_route(AccountHandlerSetV1.BASE_REST_URI, self.create_account_proxy, methods=["POST"])
        app.include_router(router)


    # attilaw: crap! mapping does not work in Router - needed a trick :-P
    # def search_accounts_proxy(self, request: Request):
    #     return self._execute_handler_method_wrapper(request=request, method=self.get_account)

    def search_accounts(self, cntx: FastAPIHttpExecutionContext) -> Response:

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Sorry... not implemented yet... :-()"
        resp = self._get_prepared_http_response(status_code = status.HTTP_501_NOT_IMPLEMENTED, bodyModel = msgResp, cntx = cntx)
        return resp


    def get_account_proxy(self, request: Request):
        account_id: str = request.path_params.get("accountId")
        if strings.is_blank(account_id):
            return self._execute_handler_method_wrapper(request=request, method=self.search_accounts)
        else:
            return self._execute_handler_method_wrapper(request=request, method=self.get_account)


    def get_account(self, cntx: FastAPIHttpExecutionContext) -> Response:
        account_id: str = cntx.http_request.path_params.get("accountId")
        account = self._account_crud_contoller.get(account_id=account_id, cntx=cntx)

        if account == None:
            raise self._get_account404_error(cntx=cntx)

        resp: Response = self._get_prepared_http_response(bodyModel=account, cntx=cntx)
        return resp
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Account - just need to declare it as param. Convenient!
    def create_account_proxy(self, request: Request, account: Account):
        resp = self._execute_handler_method_wrapper(request=request, method=self.create_account, bodyObject=account)
        return resp


    def create_account(self, cntx: FastAPIHttpExecutionContext, bodyObject: Account):

        if bodyObject.version != None and bodyObject.version != 0:
            raise MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/version", errorCodes=[CommonErrorCodes.resourceVersion_mismatch], message="If you provide 'version' of the Account resource during creation then you need to set it to 0 - or leave it out entirely."))
        # let's set version to 1
        bodyObject.version = 1

        # we take back the id
        bodyObject.id = self._account_crud_contoller.create(account_data=bodyObject, cntx=cntx)

        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Account created"
        resp = self._get_prepared_http_response(status_code = status.HTTP_201_CREATED, bodyModel = msgResp, cntx = cntx, headers={"x-account-id": bodyObject.id})
        return resp
    
    # It's really lovely in FastAPI it can automatically instantiate a pydantic Model - in our case Account - just need to declare it as param. Convenient!
    def update_account_proxy(self, request: Request, account: Account):
        resp = self._execute_handler_method_wrapper(request=request, method=self.update_account, bodyObject=account)
        return resp


    def update_account(self, cntx: FastAPIHttpExecutionContext, bodyObject: Account):

        account_id: str = cntx.http_request.path_params.get("accountId")

        # check the id!
        if bodyObject.id == None:
            bodyObject.id = account_id
        else:
            if account_id != bodyObject.id:
                # Not good!
                raise MessageResponseException(
                    cntx = cntx,
                    status_code = status.HTTP_400_BAD_REQUEST,
                    #detail = AccountAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                    problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/id", errorCodes=[CommonErrorCodes.data_contradictingRequest], message="The 'id' you provided in the body does not match with the {accountId} you provided on the URL. They must match."))

        # version must be present!
        if bodyObject.version == None:
            # Not good!
            raise MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_400_BAD_REQUEST,
                #detail = AccountAPIException.DETAILMSG_GENERIC_OP_FAILURE,
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.requestBody, placeName="/version", errorCodes=[CommonErrorCodes.information_missing], message="In updates you must provide the 'version' of the resource in the body - this should be the same as you got back when you queried the resource!"))

        try:
            self._account_crud_contoller.update(account_data = bodyObject)
        except errors.ResourceNotFoundError as exc:
            raise self._get_account404_error(cntx=cntx)
        
        msgResp: MessageResponse = self._get_prepared_MessageResponse(cntx = cntx)
        msgResp.message = "Account updated"
        resp = self._get_prepared_http_response(status_code = status.HTTP_200_OK, bodyModel = msgResp, cntx = cntx)
        return resp



    # helper method to DRY
    def _get_account404_error(self, cntx: FastAPIHttpExecutionContext) -> MessageResponseException:
        return MessageResponseException(
                cntx = cntx,
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Account does not exist",
                problems = Problem(severity=Severity.error, place=ProblemPlaceEnum.urlParam, placeName="{accountId}", errorCodes=[CommonErrorCodes.requestParameter_invalid], message="invalid accountId"))

