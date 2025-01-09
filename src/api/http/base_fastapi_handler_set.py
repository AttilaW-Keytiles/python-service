from src.model.config.models import ServiceConfig
from src.observability.logging import LoggerFactory, Logger
from src.util import dependency_validator
from fastapi import Request, FastAPI, status, Response
from src.context.contexts import FastAPIHttpExecutionContext, ExecutionContext
from pydantic import BaseModel
from abc import ABC, abstractmethod
from src.model.api.generated.common_v1 import MessageResponse, BaseResponse
from src.api.http.message_response_exception import MessageResponseException
from src.api.http.authenticator import HttpAuthenticator
from src.util import strings
from src.observability.metrics import MetricsFactory, HttpEndpointMetrics

class BaseFastAPIHandlerSet(ABC):
    """
    The superclass of all of our request handler classes. This way we can standardize behavior and provide common methods/features easily for concrete request handlers.
    """
    
    def __init__(self, service_config: ServiceConfig, authenticator: HttpAuthenticator, logger_to_use: Logger = None):
        # let's store the config
        self._service_config = service_config
        self._authenticator = authenticator
        self._LOG = logger_to_use
        if self._LOG == None:
            # let's create one to make sure things do not stay under the radar...
            self._LOG = LoggerFactory.getLogger("service.api.http.BaseHTTPHandler")

        # mark ourselves as did not attach one time things yet
        self._attached_once = False

        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='service_config', paramValueToCheck=service_config, acceptedTypes=(ServiceConfig), loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='authenticator', paramValueToCheck=authenticator, acceptedTypes=(HttpAuthenticator), loggerToUse=self._LOG)

    def attach_to_http_server(self, app: FastAPI) -> None:
        """
        After handler class is instantiated you need to invoke this method to pass over control to the handler and let it bind itself correctly.

        IMPORTANT! In subclasses try to avoid overriding this method - simply just do what you want on _do_attach_to_http_server() method implementation
        """
        # first let's do some "one time" actions...
        # in this we can attach exception handlers etc etc
        if not self._attached_once:
            self._LOG.debug("attaching one-time things to FastAPI app...")
            app.add_exception_handler(MessageResponseException, self.messageresponse_exception_handler)
            self._attached_once = True
            self._LOG.debug("one-time things done!")
        
        # and now allow the subclass to attach himself too
        self._do_attach_to_http_server(app=app)

    @abstractmethod
    def _do_attach_to_http_server(self, app: FastAPI) -> None:
        """
        Abstract method - derived handler classes should implement and bind themselves here - DO NOT override the 'attach_to_http_server()' method! No point. This method is invoked from there.
        """
        ...
        

    # This handler is registered to deal with MessageResponseException - which we convert into MessageResponse
    # This helps us to fulfill our contract
    def messageresponse_exception_handler(self, request: Request, exc: MessageResponseException):
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
    

    # Subclasses can use this method to build a context
    def _create_execution_context(self, http_request: Request) -> FastAPIHttpExecutionContext:
        cntx = FastAPIHttpExecutionContext(http_request=http_request)
        return cntx
    
    def _execute_handler_method_wrapper(self, request: Request, method, endpoint_name: str = None, bodyObject: BaseModel = None, logRequestOnLevel: str = "info", logRequestBodyOnLevel: str = "info"):
        """
        Used by _proxy_ methods. It executes the given method "wrapped" - to ensure all boilerplate is done and exceptions handled correctly.

        This way the methods who are running wrapped can really and purely focus on their business logic.
        """
        # as firs step - we need a context derived from the inbound request
        cntx: FastAPIHttpExecutionContext = self._create_execution_context(http_request=request)
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()

        resp: Response = None

        # create set of counters metrics - if we know the endpoint name somehow...
        http_metrics: HttpEndpointMetrics = None
        if endpoint_name == None:
            endpoint_name = request.url.path
            # careful!! if we have parameters in the path - we do not want to create tons of this for each concrete value...
            # so let's do something tricky :-P
            for key, value in request.path_params.items():
                endpoint_name = endpoint_name.replace(value, f":{key}:")
        if endpoint_name != None:
            http_metrics = MetricsFactory.get_http_endpoint_metrics(endpoint_name = endpoint_name)

        # things could go wrong... so let's wrap it!
        try:
            # authentication
            self._authenticator.authenticate_if_present(request=request, cntx=cntx)

            self._log_inbound_request(http_request=request, onLevel=logRequestOnLevel, cntx=cntx)
            if bodyObject != None:
                if not isinstance(logRequestBodyOnLevel, str):
                    logRequestBodyOnLevel = str(logRequestBodyOnLevel)
                logRequestBodyOnLevel = logRequestBodyOnLevel.lower()
                if logRequestBodyOnLevel == "debug":
                    self._LOG.debug("request bodyObject is: [[%s]]", bodyObject, **labels)
                elif logRequestBodyOnLevel == "info":
                    self._LOG.info("request bodyObject is: [[%s]]", bodyObject, **labels)

            if bodyObject == None:
                resp = method(cntx)
            else:
                resp = method(cntx, bodyObject)
            
        except MessageResponseException as exc:
            # metrics! if we have...
            if http_metrics != None:
                http_metrics.increment(status_code = exc.status_code, method = request.method)
            # just simply throw it
            raise exc
        except Exception as exc:
            msgRespException = MessageResponseException.from_exception(exc=exc, cntx=cntx)
            # metrics! if we have...
            if http_metrics != None:
                http_metrics.increment(status_code = msgRespException.status_code, method = request.method)
            # throw it the way we set the cause too
            raise msgRespException from exc
        finally:
            tookMillis = cntx.get_ellapsed_millis()
            self._LOG.debug("Req-Resp completed - took %s millis", tookMillis, **labels)

        # metrics! if we have...
        if http_metrics != None:
            http_metrics.increment(status_code = resp.status_code, method = request.method)
        
        return resp
    
    
    # Subclasses can use this method get a prepared skeleton of MessageResponse
    def _get_prepared_MessageResponse(self, cntx: ExecutionContext = None) -> MessageResponse:
        base_resp = self._get_prepared_BaseResponse(cntx = cntx)
        msgResp = MessageResponse(requestReceivedAt = base_resp.requestReceivedAt, processingTookMillis = base_resp.processingTookMillis)
        return msgResp

    # Subclasses can use this method get a prepared skeleton of BaseResponse
    def _get_prepared_BaseResponse(self, cntx: ExecutionContext = None) -> BaseResponse:
        receivedAt = -1
        tookMillis = None
        if cntx != None:
            receivedAt = int(cntx.created_ts)
            tookMillis = cntx.get_ellapsed_millis()
        msgResp = BaseResponse(requestReceivedAt = receivedAt, processingTookMillis = tookMillis)
        return msgResp


    # Subclass can obtain clienbt IP address
    def _get_client_IP(self, http_request: Request) -> str:
        forwardedFor = http_request.headers.get("x-forwarded-for")
        if forwardedFor == None:
            forwardedFor = http_request.headers.get("x-forwardedfor")
        if forwardedFor != None:
            return forwardedFor
        return str(http_request.client)
    
    # Subclasses can use this to dump the requ details into log
    def _log_inbound_request(self, http_request: Request, cntx: ExecutionContext = None, onLevel: str = "info") -> None:
        """
        Logs out the incoming request details - unless 'onLevel=none' ... otherwise 'onLevel' is used where valid values are "info", "debug" or "none"
        """
        if self._LOG == None:
            return
        
        if not isinstance(onLevel, str):
            onLevel = str(onLevel)
        onLevel = onLevel.lower()
        if onLevel != "info" and onLevel != "debug":
            return
        onDebugLevel = onLevel == "debug"

        query_args = http_request.url.query
        if query_args != "":
            query_args = "?"+query_args
        ipAddr = self._get_client_IP(http_request=http_request)
        method = http_request.method

        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        if onDebugLevel:
            self._LOG.debug("incoming %s request '%s%s' from %s", method, http_request.url.path, query_args, ipAddr, **labels)
        else:
            self._LOG.info("incoming %s request '%s%s' from %s", method, http_request.url.path, query_args, ipAddr, **labels)
            

    # Subclasses can use this to get a prepared Response object
    def _get_prepared_http_response(self, status_code: int = status.HTTP_200_OK, bodyModel: BaseModel = None, cntx: ExecutionContext = None, headers: dict[str, str] = None) -> Response:
        
        content = ""
        if bodyModel != None:
            content = bodyModel.model_dump_json()

        # start basic
        resp = Response(
            status_code = status_code,
            media_type = "application/json",
            content = content
        )

        # assemble headers
        respHeaders = dict()
        if headers != None:
            # TODO we should make sure all values are converted to str! Otherwise if user puts in an 'int' for example then an error is raised
            respHeaders.update(headers)
        # we add headers from the context 2nd step - because they take precedence in case of conflict
        if cntx != None:
            respHeaders.update(cntx.get_http_response_headers())
        resp.headers.update(respHeaders)

        return resp





