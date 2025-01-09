
from src.context.contexts import ExecutionContext
from src.model.auth.auth_info import AuthInfo
from src.model.error import errors

class Authorization:

    @staticmethod
    def ensureHasRole(cntx: ExecutionContext, anyOf: set[str]) -> None:
        """
        Authorization - method takes roles and ensures caller has one of them. If not then AuthorizationError is raised. Otherwise nothing happens but returns.
        """

        auth_info = cntx.get_auth() if cntx != None else None
        if auth_info != None:
            for role in anyOf:
                if auth_info.has_role:
                    # we are good
                    return

        # OOps
        raise errors.AuthorizationError(
            message = "You do not have permission for this operation, sorry..."
        )        

