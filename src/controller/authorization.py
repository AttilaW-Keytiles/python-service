
from src.context.contexts import ExecutionContext
from src.model.auth.auth_info import AuthInfo
from src.model.error import errors
from src.observability.logging import Logger, LoggerFactory

class Authorization:

    _LOG: Logger = LoggerFactory.getLogger("service.controller.Authorization")

    @staticmethod
    def ensureHasRole(cntx: ExecutionContext, anyOf: set[str]) -> None:
        """
        Authorization - method takes roles and ensures caller has one of them. If not then AuthorizationError is raised. Otherwise nothing happens but returns.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        Authorization._LOG.debug("ensureHasRole - anyOf: %s", anyOf)

        auth_info = cntx.get_auth() if cntx != None else None
        if auth_info != None:
            for role in anyOf:
                if auth_info.has_role(role):
                    # we are good
                    Authorization._LOG.debug("role '%s' found - OK", role, **labels)
                    return

        # Oops
        Authorization._LOG.error("Authorization failed - raising AuthorizationError ...", **labels)
        raise errors.AuthorizationError(
            message = "You do not have permission for this operation, sorry..."
        )        

