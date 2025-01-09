from abc import ABC, abstractmethod
from src.context.contexts import ExecutionContext
from src.model.db.models import User
from src.observability.logging import LoggerFactory, Logger
from src.util import dependency_validator
from src.model.config.models import ServiceConfig
from fastapi import Request
from src.model.error import errors
from src.model.auth.auth_info import AuthInfo
from src.model.auth import roles
import base64


class IUserProvider(ABC):
    """
    Interface (Port) which declares what is needed by `HttpAuthenticator`.
    We can have concrete implementations (Adapters) in the 'persistence' package.
    """
    # Implementors SHOULD use these error codes when running into problem
    ERRCODE_READ_USER_BY_USERNAME_FAILED = "user_db_read_user_by_username_failed"

    @abstractmethod
    def get_user_by_username(self, user_name: str, cntx: ExecutionContext) -> User|None:
        """
        Retrieves a User record from the DB by username. Or None if not found.
        """

class HttpAuthenticator:
    """
    This is an adapter basically. Adapter btw our HttpRequest handlers and its auth concept AND `~src.model.auth.auth_info.AuthInfo` which is actually part of `~src.context.contexts.ExecutionContext`

    For now we support only Basic auth
    """
    def __init__(self, config: ServiceConfig, user_provider: IUserProvider):
        self._LOG: Logger = LoggerFactory.getLogger("service.api.http.HttpAuthenticator")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=ServiceConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='user_provider', paramValueToCheck=user_provider, acceptedTypes=IUserProvider, loggerToUse=self._LOG)

        self._config: ServiceConfig = config
        self._user_provider: IUserProvider = user_provider
   
    def authenticate_if_present(self, request: Request, cntx: ExecutionContext) -> None:
        """
        When control passed to this method then it is taking possible Auth from the request and if successful then
        converts it and places it into the ExecutionContext.

        In case something goes wrong might raise:
         * `~src.model.error.errors.AuthenticationError`
        """

        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()

        # let's get the header!
        auth_header = request.headers.get("Authorization")
        if auth_header == None:
            # nothing to do
            self._LOG.debug("no auth header - skipping", **labels)
            return
        
        try:
            if auth_header.startswith("Basic "):
                self._LOG.debug("'Basic' auth header found - on it...", **labels)

                token: str = auth_header.replace("Basic ", "")
                token = base64.b64decode(token).decode("ascii")
                parts: list[str] = token.split(":")
                username = parts[0]
                pwd = parts[1]

                self._LOG.debug("decoded", **labels)

                user: User = self._user_provider.get_user_by_username(user_name=username, cntx=cntx)
                # TODO for now password is just raw - not good... fix it
                if user == None or user.password != pwd:
                    self._LOG.warning("no matching User or pwd mismatch - failed", **labels)
                    # unknown user
                    raise errors.AuthenticationError(
                        message = "Wrong credentials - authentication failed",
                        error_codes = errors.AuthenticationError.ERROR_FAILED
                    )
                # convert and deploy
                auth_info: AuthInfo = AuthInfo(
                    user_id = user.id,
                    user_name = user.username,
                    # for now everyone is employee
                    roles = [roles.AUTH_ROLE_EMPLOYEE]
                )
                self._LOG.debug("user authenticated successfully: %s", auth_info, **labels)
                cntx.set_auth(auth_info = auth_info)
                return

        except Exception as e:
            self._LOG.error("Something went wrong... error was: %s", e, **labels)
            # CAREFUL! Do not leak sensitive info into responsee!!!
            raise errors.AuthenticationError(
                message = "Authentication failed - something went wrong, sorry...",
                error_codes = errors.AuthenticationError.ERROR_FAILED
            )
        
        # if we are here then well...
        self._LOG.error("Method is unsupported on header value: '%s'", auth_header, **labels)
        raise errors.AuthenticationError(
            message = "Authentication failed - method you are using is not supported, sorry...",
            error_codes = errors.AuthenticationError.ERROR_NOT_SUPPORTED
        )

