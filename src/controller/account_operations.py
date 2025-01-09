from src.model.api.generated.banking_api_v1 import Transfer, TransferDirection, Account
from src.controller.account_crud import IAccountCRUD_DAO
from src.controller.customer_crud import ICustomerCRUD_DAO
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings
from src.context.contexts import ExecutionContext
from src.model.config.models import ServiceConfig
from src.model.error import errors
from abc import ABC, abstractmethod
from copy import deepcopy
from src.controller.authorization import Authorization
from src.model.auth import roles


class IAccountOperations_DAO(ABC):
    """
    Interface (Port) which declares certain support we need from persistence layer regarding Accounts - needed by `AccountOperationsController`.

    We can have concrete implementations (Adapters) in the 'persistence' package.

    IMPORTANT! In implementations when you are raising `~src.model.error.errors.ServiceRuntimeError`s please use the appropriate ERRCODE_xxx_FAILED constant as error_code!
    """

    # Implementors SHOULD use these error codes when running into problem
    ERRCODE_GET_ACCOUNTTRANSFERS_FAILED = "account_db_getaccounttransfers_failed"
    ERRCODE_GET_CUSTOMERACCOUNTS_FAILED = "account_db_getcustomeraccounts_failed"

    @abstractmethod
    def get_account_transfers(self, account_id: str, direction: TransferDirection = TransferDirection.all, cntx: ExecutionContext = None) -> list[Transfer]: 
        """
        Retrieves Transfers belong to a specific Account and returns them in an ordered list. Order should be time descendant.

        The `direction` parameter tells what we are curious about - obvious hopefully...

        If there is no match return empty list (but never None ideally...)

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def get_customer_accounts(self, customer_id: str, cntx: ExecutionContext = None) -> list[Account]: 
        """
        Retrieves all Accounts belong to a specific Customer.

        If there is no match return empty list (but never None ideally...)

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...


class AccountOperationsController:
    """
    This controller is responsible for providing support to apply/execute Account related operations which do not fit into CRUD (RESTful) approach.

    This class is in the core of application business logic! In "Clean architecture" principles actually it is implementing so called "Use cases".

    For persistence purposes it has a dependency on the defined interface `IAccountOperations_DAO`
    and you must inject an implementation during construct time.
    """

    def __init__(self, config: ServiceConfig, account_ops_DAO: IAccountOperations_DAO, account_crud_DAO: IAccountCRUD_DAO, customer_crud_DAO: ICustomerCRUD_DAO):
        self._LOG: Logger = LoggerFactory.getLogger("service.controller.AccountOperationsController")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=ServiceConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='account_ops_DAO', paramValueToCheck=account_ops_DAO, acceptedTypes=IAccountOperations_DAO, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='account_crud_DAO', paramValueToCheck=account_crud_DAO, acceptedTypes=IAccountCRUD_DAO, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='customer_crud_DAO', paramValueToCheck=customer_crud_DAO, acceptedTypes=ICustomerCRUD_DAO, loggerToUse=self._LOG)

        self._account_ops_DAO: IAccountOperations_DAO = account_ops_DAO
        self._account_crud_DAO: IAccountCRUD_DAO = account_crud_DAO
        self._customer_crud_DAO: ICustomerCRUD_DAO = customer_crud_DAO


    def get_account_transfers(self, account_id: str, direction: TransferDirection = TransferDirection.all, cntx: ExecutionContext = None) -> list[Transfer]: 
        """
        Retrieves Transfers belong to a specific Account and returns them in an ordered list. Order should be time descendant.

        The `direction` parameter tells what we are curious about - obvious hopefully...

        If there is no match returns empty list.
        If the requested Account does not exist then `ResourceNotFoundError` is raised.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving '%s' Transfers of Account id=%s", direction, account_id, **labels)

        # if no permission, stop right here
        Authorization.ensureHasRole(cntx = cntx, anyOf = {roles.AUTH_ROLE_EMPLOYEE})

        preconditions.check_argument(strings.is_not_blank(account_id), "'account_id' can not be blank")
        # this account must exist
        existing_account = self._account_crud_DAO.read(account_id=account_id, cntx=cntx)
        if existing_account == None:
            if existing_account == None:
                # Oops it does not exist
                err: str = f"Failed to retrieve Transfers for Account - Account id '{account_id}' does not exist"
                self._LOG.error(err, **labels)
                raise errors.ResourceNotFoundError(message=err)            

        transfers: list[Transfer] = self._account_ops_DAO.get_account_transfers(account_id=account_id, direction=direction, cntx=cntx)

        if transfers == None:
            transfers = list()

        return transfers
    
    
    def get_customer_accounts(self, customer_id: str, cntx: ExecutionContext = None) -> list[Account]:
        """
        Retrieves all Accounts belong to a specific Customer.

        If there is no match returns empty list. If the requested Customer does not exist then `ResourceNotFoundError` is raised.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving Accounts for Customer id=%s", customer_id, **labels)

        # if no permission, stop right here
        Authorization.ensureHasRole(cntx = cntx, anyOf = {roles.AUTH_ROLE_EMPLOYEE})

        preconditions.check_argument(strings.is_not_blank(customer_id), "'customer_id' can not be blank")

        # this customer must exist
        existing_customer = self._customer_crud_DAO.read(customer_id=customer_id, cntx=cntx)
        if existing_customer == None:
            if existing_customer == None:
                # Oops it does not exist
                err: str = f"Failed to retrieve Accounts for Customer - Customer id '{customer_id}' does not exist"
                self._LOG.error(err, **labels)
                raise errors.ResourceNotFoundError(message=err)

        accounts: list[Account] = self._account_ops_DAO.get_customer_accounts(customer_id=customer_id, cntx=cntx)
        if accounts == None:
            accounts = list()

        return accounts




