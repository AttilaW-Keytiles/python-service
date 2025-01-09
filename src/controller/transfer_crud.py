from src.model.api.generated.banking_api_v1 import Transfer, TransferStatus, AccountStatus
from src.controller.account_crud import IAccountCRUD_DAO
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings
from src.context.contexts import ExecutionContext
from src.model.config.models import ServiceConfig
from src.model.error import errors
from abc import ABC, abstractmethod
from copy import deepcopy
import time
from decimal import Decimal, ROUND_HALF_UP
from src.controller.authorization import Authorization
from src.model.auth import roles


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

        self._transfer_DAO: ITransferCRUD_DAO = transfer_DAO
        self._account_DAO: IAccountCRUD_DAO = account_DAO
        self._config: ServiceConfig = config

    def _round_to_Xdecimals(self, val: float, cntx: ExecutionContext = None) -> float:
        # a Decimal object with an explicit exponent attribute/property (to be interpreted by quantize)
        x_places = Decimal("1e-" + str(self._config.business_logic.roundig_decimals))
        rounded = float(Decimal(val).quantize(x_places, rounding=ROUND_HALF_UP))
        if rounded != val:
            # better to always know about this
            labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
            self._LOG.info("rounding applied for configured %s decimals: %s -> %s", self._config.business_logic.roundig_decimals, val, rounded, **labels)
        return rounded

    def create(self, transfer_data: Transfer, cntx: ExecutionContext = None) -> None:
        """
        Creates a Transfer - based on the passed Transfer data.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("creating Transfer: %s", transfer_data, **labels)

        # if no permission, stop right here
        Authorization.ensureHasRole(cntx = cntx, anyOf = {roles.AUTH_ROLE_EMPLOYEE})

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
        # this id should be free and not exist
        existing_transfer = self._transfer_DAO.read(transfer_id = transfer_data.id, cntx=cntx)
        if existing_transfer != None:
            # Oops...
            err: str = f"Failed to insert Transfer - already exists"
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN})
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
        # destination account is mandatory...
        if strings.is_blank(transfer_data.destinationAccountId):
            # Oops...
            err: str = f"Failed to create Transfer - 'destinationAccountId' is mandatory information which was not provided or was empty. You should provide it!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_MISSING_MANDATORY}, place_name = "transfer_data.destinationAccountId")
        # source and dest can not be the same
        if transfer_data.sourceAccountId == transfer_data.destinationAccountId:
            # Oops...
            err: str = f"Failed to create Transfer - 'destinationAccountId' can not be the same as 'sourceAccountId'!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "transfer_data.destinationAccountId")
        # source account must exist!
        source_account_obj = self._account_DAO.read(account_id = transfer_data.sourceAccountId, cntx = cntx)
        if source_account_obj == None:
            # Oops
            err: str = f"Failed to create Transfer - provided 'sourceAccountId' is invalid - this account does not exist!"
            self._LOG.error(err, **labels)
            raise errors.ValidationError(message=err, error_codes={errors.ValidationError.ERRCODE_INVALID_VALUE}, place_name = "transfer_data.sourceAccountId")
        # destination account must exist!
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

        # at tis point
        # round amount to 2 decimals no matter what came in
        transfer_data.amount = self._round_to_Xdecimals(transfer_data.amount, cntx=cntx)

        # OK now let's validate a few states - pretty much business logic

        # does have the source account enough money?
        if source_account_obj.balance < transfer_data.amount:
            # Oops...
            err: str = f"Failed to create Transfer - source Account does not have enough money..."
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={"not_enough_balance"})
        # is the source account active?
        if source_account_obj.status != AccountStatus.active:
            # Oops...
            err: str = f"Failed to create Transfer - source Account status is not Active..."
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={"src_account_invalid_status"})
        # is the dest account active?
        if destination_account_obj.status != AccountStatus.active:
            # Oops...
            err: str = f"Failed to create Transfer - destionation Account status is not Active..."
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={"dst_account_invalid_status"})

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
        # reduce math problems of float a bit - round 2 decimals
        source_account_obj.balance = self._round_to_Xdecimals(source_account_obj.balance, cntx=cntx)
        destination_account_obj.balance = self._round_to_Xdecimals(destination_account_obj.balance, cntx=cntx)
        # let's persist!
        self._account_DAO.upsert(account_data = source_account_obj)
        self._account_DAO.upsert(account_data = destination_account_obj)

        # this means the transaction is settled
        transfer_data.status = TransferStatus.settled
        # and let's persist!
        self._transfer_DAO.insert(transfer_data = transfer_data)

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

        # if no permission, stop right here
        Authorization.ensureHasRole(cntx = cntx, anyOf = {roles.AUTH_ROLE_EMPLOYEE})

        preconditions.check_argument(strings.is_not_blank(transfer_id), "'transfer_id' can not be blank")

        transfer: Transfer = self._transfer_DAO.read(transfer_id=transfer_id, cntx=cntx)

        if transfer == None:
            self._LOG.debug("not found", **labels)

        return transfer


