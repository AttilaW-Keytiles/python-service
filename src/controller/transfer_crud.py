from src.model.api.generated.banking_api_v1 import Transfer, TransferStatus
from src.controller.account_crud import IAccountCRUD_DAO
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings, ids
from src.context.contexts import ExecutionContext
from src.model.config.models import ServiceConfig
from src.model.error import errors
from abc import ABC, abstractmethod
from copy import deepcopy
import time


class ITransferCRUD_DAO(ABC):
    """
    Interface (Port) which declares basic CRUD operations for persisting Transfers - needed by `TransferCRUDController`.

    We can have concrete implementations (Adapters) in the 'persistence' package.

    IMPORTANT! In implementations when you are raising `~src.model.error.errors.ServiceRuntimeError`s please use the appropriate ERRCODE_xxx_FAILED constant as error_code!
    """

    # Implementors SHOULD use these error codes when running into problem
    ERRCODE_UPSERT_FAILED = "transfer_db_upsert_failed"
    ERRCODE_READ_FAILED = "transfer_db_read_failed"
    ERRCODE_DELETE_FAILED = "transfer_db_delete_failed"

    @abstractmethod
    def insert(self, transfer_data: Transfer, cntx: ExecutionContext = None) -> None:
        """
        Inserts the given Transfer in persistence.

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def read(self, transfer_id: str, cntx: ExecutionContext = None) -> Union[Transfer|None]: 
        """
        Retrieves a Transfer from the persistence who's ID is `transfer_id` or returns None if not found

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...


class TransferCRUDController:
    """
    This controller is responsible for providing CRUD operations for Transfers.

    This class is in the core of application business logic! In "Clean architecture" principles actually it is implementing so called "Use cases".

    For persistence purposes it has a dependency on the defined interface `ITransferCRUD_DAO`
    and you must inject an implementation during construct time.
    """

    # Quick note: we need the IAccountCRUD_DAO too to see and validate Accounts exists and also modify their balances
    def __init__(self, config: ServiceConfig, transfer_DAO: ITransferCRUD_DAO, account_DAO: IAccountCRUD_DAO):
        self._LOG: Logger = LoggerFactory.getLogger("service.controller.TransferCRUDController")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=ServiceConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='transfer_DAO', paramValueToCheck=transfer_DAO, acceptedTypes=ITransferCRUD_DAO, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='account_DAO', paramValueToCheck=account_DAO, acceptedTypes=IAccountCRUD_DAO, loggerToUse=self._LOG)

        self._transfer_DAO = transfer_DAO
        self._account_DAO = account_DAO


    def create(self, transfer_data: Transfer, cntx: ExecutionContext = None) -> None:
        """
        Creates a Transfer - based on the passed Transfer data.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("creating Transfer: %s", transfer_data, **labels)
        preconditions.check_argument(transfer_data != None and isinstance(transfer_data, Transfer), "'transfer_data' parameter must be provided and it must be Transfer type")
        # we should not modify the passed in object - so take a copy
        transfer_data = deepcopy(transfer_data)

        # validations

        # id assignment on client side is mandatory
        if strings.is_blank(transfer_data.id):
            # Oops...
            err: str = f"Failed to create Transfer - 'id' is mandatory information which was not provided or was empty. You should provide a valid UUID for the Transfer!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "transfer_data.id")
        # amount must be there and must be positive
        if transfer_data.amount == None:
            # Oops...
            err: str = f"Failed to create Transfer - 'amount' is mandatory information you must provide it"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "transfer_data.amount")
        if transfer_data.amount <= 0:
            # Oops...
            err: str = f"Failed to create Transfer - 'amount' must be >0"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "transfer_data.amount")
        # source account is mandatory...
        if strings.is_blank(transfer_data.sourceAccountId):
            # Oops...
            err: str = f"Failed to create Transfer - 'sourceAccountId' is mandatory information which was not provided or was empty. You should provide it!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "transfer_data.sourceAccountId")
        # and must exist!
        source_account_obj = self._account_DAO.read(account_id = transfer_data.sourceAccountId, cntx = cntx)
        if source_account_obj == None:
            # Oops
            err: str = f"Failed to create Transfer - provided 'sourceAccountId' is invalid - this account does not exist!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "transfer_data.sourceAccountId")
        # destination account is mandatory...
        if strings.is_blank(transfer_data.destinationAccountId):
            # Oops...
            err: str = f"Failed to create Transfer - 'destinationAccountId' is mandatory information which was not provided or was empty. You should provide it!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "transfer_data.destinationAccountId")
        # and must exist!
        destination_account_obj = self._account_DAO.read(account_id = transfer_data.destinationAccountId, cntx = cntx)
        if destination_account_obj == None:
            # Oops
            err: str = f"Failed to create Transfer - provided 'destinationAccountId' is invalid - this account does not exist!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "transfer_data.destinationAccountId")
        # status is read-only
        if transfer_data.status != None:
            # Oops...
            err: str = f"Failed to create Transfer - 'status' was provided however not expected as we maintain that always on server side. Should not be sent."
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED}, place_name = "transfer_data.status")
        # createdAt is read-only
        if transfer_data.createdAt != None:
            # Oops...
            err: str = f"Failed to create Transfer - 'createdAt' timestamp was provided however not expected as we generate it always on server side. Should not be sent."
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED}, place_name = "transfer_data.createdAt")
        # createdBy is read-only
        if transfer_data.createdBy != None:
            # Oops...
            err: str = f"Failed to create Transfer - 'createdAt' timestamp was provided however not expected as we generate it always on server side. Should not be sent."
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED}, place_name = "transfer_data.createdAt")

        # does have the source account enough money?
        if source_account_obj.balance < transfer_data.amount:
            # Oops...
            err: str = f"Failed to create Transfer - source Account does not have enough money..."
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={"not_enough_balance"})

        # current time
        transfer_data.createdAt = int(time.time())
        # who did it???
        created_by = "?"
        if cntx != None and cntx.auth_info != None:
            # lets inherit that in!
            created_by = cntx.auth_info.user_name
        transfer_data.createdBy = created_by

        # This is a point we should really make logs to hae some audit - on INFO level
        self._LOG.info("Just about to execute Transaction: %s", transfer_data, **labels)
        self._LOG.info("source account balance BEFORE transaction is: %s", source_account_obj.balance, **labels)
        self._LOG.info("destination account balance BEFORE transaction is: %s", destination_account_obj.balance, **labels)

        # !!!!!!!! TODO DB transaction should begin here!
        # but for now lets just do it

        source_account_obj.balance -= transfer_data.amount
        destination_account_obj.balance += transfer_data.amount
        # let's persist!
        self._account_DAO.upsert(account_data = source_account_obj)
        self._account_DAO.upsert(account_data = destination_account_obj)

        # this means the transaction is settled
        transfer_data.status = TransferStatus.settled
        # and let's persist!
        self._transfer_DAO.create(transfer_data = transfer_data)

        # !!!!!!! DB transaction ends here

        self._LOG.info("Transaction id='%s' is complete! ", transfer_data.id, **labels)
        self._LOG.info("source account balance AFTER transaction is: %s", source_account_obj.balance, **labels)
        self._LOG.info("destination account balance AFTER transaction is: %s", destination_account_obj.balance, **labels)


    def get(self, transfer_id: str, cntx: ExecutionContext = None) -> Union[Transfer|None]:
        """
        Retrieves a Transfer belongs to 'transfer_id' - if exists.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving Transfer id=%s", transfer_id, **labels)

        preconditions.check_argument(strings.is_not_blank(transfer_id), "'transfer_id' can not be blank")

        transfer: Transfer = self._transfer_DAO.read(transfer_id=transfer_id, cntx=cntx)

        if transfer == None:
            self._LOG.debug("not found", **labels)

        return transfer


