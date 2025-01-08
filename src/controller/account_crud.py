from src.model.api.generated.banking_api_v1 import Account, AccountStatus
from src.controller.customer_crud import ICustomerCRUD_DAO
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings, ids
from src.context.contexts import ExecutionContext
from src.model.config.models import ServiceConfig
from src.model.error import errors
from abc import ABC, abstractmethod
from copy import deepcopy
import time


class IAccountCRUD_DAO(ABC):
    """
    Interface (Port) which declares basic CRUD operations for persisting Accounts - needed by `AccountCRUDController`.

    We can have concrete implementations (Adapters) in the 'persistence' package.

    IMPORTANT! In implementations when you are raising `~src.model.error.errors.ServiceRuntimeError`s please use the appropriate ERRCODE_xxx_FAILED constant as error_code!
    """

    # Implementors SHOULD use these error codes when running into problem
    ERRCODE_UPSERT_FAILED = "account_db_upsert_failed"
    ERRCODE_READ_FAILED = "account_db_read_failed"
    ERRCODE_DELETE_FAILED = "account_db_delete_failed"

    @abstractmethod
    def upsert(self, account_data: Account, cntx: ExecutionContext = None) -> None:
        """
        Inserts / Updates the given Account in persistence.

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def read(self, account_id: str, cntx: ExecutionContext = None) -> Union[Account|None]: 
        """
        Retrieves a Account from the persistence who's ID is `account_id` or returns None if not found

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...


class AccountCRUDController:
    """
    This controller is responsible for providing CRUD operations for Accounts.

    This class is in the core of application business logic! In "Clean architecture" principles actually it is implementing so called "Use cases".

    For persistence purposes it has a dependency on the defined interface `IAccountCRUD_DAO`
    and you must inject an implementation during construct time.
    """

    # Quick note: we need the ICustomerCRUD_DAO too to validate Customer exists
    def __init__(self, config: ServiceConfig, account_DAO: IAccountCRUD_DAO, customer_DAO: ICustomerCRUD_DAO):
        self._LOG: Logger = LoggerFactory.getLogger("service.controller.AccountCRUDController")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=ServiceConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='account_DAO', paramValueToCheck=account_DAO, acceptedTypes=IAccountCRUD_DAO, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='customer_DAO', paramValueToCheck=customer_DAO, acceptedTypes=ICustomerCRUD_DAO, loggerToUse=self._LOG)

        self._account_DAO = account_DAO
        self._customer_DAO = customer_DAO


    def _generate_new_bank_account_id(self) -> str:
        valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        id = ids.generate_random_word(4, valid_chars) + "-"
        id = id + ids.generate_random_word(4, valid_chars) + "-"
        id = id + ids.generate_random_word(4, valid_chars) + "-"
        id = id + ids.generate_random_word(4, valid_chars)
        return id


    def create(self, account_data: Account, cntx: ExecutionContext = None) -> str:
        """
        Creates a Account - based on the passed Account data.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("creating Account: %s", account_data, **labels)
        preconditions.check_argument(account_data != None and isinstance(account_data, Account), "'account_data' parameter must be provided and it must be Account type")
        # we should not modify the passed in object - so take a copy
        account_data = deepcopy(account_data)

        # validations

        # customer_id is mandatory
        if strings.is_blank(account_data.customerId):
            # Oops...
            err: str = f"Failed to create Account - 'customerId' is mandatory information which was not provided or was empty. You should provide a valid customerId!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "account_data.customerId")
        # does it exist?
        customer_obj = self._customer_DAO.read(customer_id = account_data.customerId, cntx = cntx)
        if customer_obj == None:
            # Oops
            err: str = f"Failed to create Account - provided 'customerId' is invalid - this customer does not exist!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "account_data.customerId")
        
        # we always generate account ids on server side - so it should not be provided by the caller
        if account_data.id != None:
            # Oops...
            err: str = f"Failed to create Account - 'id' was provided however not expected as we generate it always on server side. Should not be sent."
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED}, place_name = "account_data.id")
        # we always generate this
        if account_data.createdAt != None:
            # Oops...
            err: str = f"Failed to create Account - 'createdAt' timestamp was provided however not expected as we generate it always on server side. Should not be sent."
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED}, place_name = "account_data.createdAt")

        is_unique = False
        while not is_unique:
            # let's generate a bank account
            account_data.id = self._generate_new_bank_account_id()
            existing_account: Account = self._account_DAO.read(account_data.id)
            is_unique = existing_account == None

        # now version stuff - we must persist with v1
        account_data.version = 1
        # current time
        account_data.createdAt = int(time.time())

        # defaults - if not provided
        if account_data.balance == None:
            account_data.balance = 0
        if account_data.status == None:
            account_data.status = AccountStatus.active
        else:
            # we need to check the value - it must be one of the valid enum values
            if not preconditions.is_enum_value_valid(account_data.status, AccountStatus):
            # Oops
                err: str = f"Failed to create Account - provided 'status' is not a valid Account status!"
                self._LOG.error(err, **labels)
                raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "account_data.status")

        # and lest go!
        self._account_DAO.upsert(account_data = account_data, cntx = cntx)
        return account_data.id


    def get(self, account_id: str, cntx: ExecutionContext = None) -> Union[Account|None]:
        """
        Retrieves a Account belongs to 'account_id' - if exists.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving Account id=%s", account_id, **labels)

        preconditions.check_argument(strings.is_not_blank(account_id), "'account_id' can not be blank")

        account: Account = self._account_DAO.read(account_id=account_id, cntx=cntx)

        if account == None:
            self._LOG.debug("not found", **labels)

        return account


    def update(self, account_data: Account, cntx: ExecutionContext = None):
        """
        Updates an existing Account to match with the given attributes.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("updating Account: %s", account_data, **labels)

        preconditions.check_argument(account_data != None and isinstance(account_data, Account), "'account_data' parameter must be provided and it must be Account type")
        # we should not modify the passed in object - so take a copy
        #account_data = deepcopy(account_data)

        if account_data.id != None:
            # Oops...
            err: str = f"Failed to update Account - 'id' was not provided however it is mandatory"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "account_data.id")

        # the underlying DAO is upsert based - but now we have an update
        # so to avoid we create the Account instead of updating an existing we need a read back first
        existing_account: Account = self._account_DAO.read(account_data.id)
        if existing_account == None:
            # Oops it does not exist
            err: str = f"Failed to update Account - id '{account_data.id}' does not exist"
            self._LOG.error(err, **labels)
            raise errors.ResourceNotFoundError(message=err)

        # so we have the guy!
        # let's check the versions - any optimistic locking problem?
        if existing_account.version != account_data.version:
            # Oops it does not work...
            err: str = f"Failed to update Account - assumed and actual resource versions do not match! Very likely someone else has updated this resource in the meantime - please read it again!"
            self._LOG.error(err, **labels)
            raise errors.OptimisticLockingError(message = err, error_codes = errors.OptimisticLockingError.ERRCODE_VERSION_CONFLICT, assumed_version=account_data.version, actual_version=existing_account.version)

        # time to validate some info

        # some fields should not be provided or if yes then not changed (read only)
        if account_data.createdAt != None and account_data.createdAt != existing_account.createdAt:
            # Oops...
            err: str = f"Failed to update Account - 'createdAt' is a read-only field which you tried to change"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_READONLY_VALUE_CHANGED}, place_name = "account_data.createdAt")

        if account_data.customerId != None and account_data.customerId != existing_account.customerId:
            # does the new owner exist?
            customer_obj = self._customer_DAO.read(customer_id = account_data.customerId, cntx = cntx)
            if customer_obj == None:
                # Oops
                err: str = f"Failed to update Account - provided 'customerId' is invalid - this customer does not exist!"
                self._LOG.error(err, **labels)
                raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "account_data.customerId")
            # merge it in
            existing_account.customerId = account_data.customerId

        if account_data.status != None and account_data.status != existing_account.status:
            # we need to check the value - it must be one of the valid enum values
            if not preconditions.is_enum_value_valid(account_data.status, AccountStatus):
            # Oops
                err: str = f"Failed to create Account - provided 'status' is not a valid Account status!"
                self._LOG.error(err, **labels)
                raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "account_data.status")
            # merge it in
            existing_account.status = account_data.status

        if account_data.balance != None:
            existing_account.balance = account_data.balance
        
        # version should be increased
        existing_account.version = existing_account.version + 1

        self._account_DAO.upsert(account_data = existing_account, cntx = cntx)


