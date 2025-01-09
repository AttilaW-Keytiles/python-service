from src.model.api.generated.banking_api_v1 import Customer
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings, ids
from src.context.contexts import ExecutionContext
from src.model.config.models import ServiceConfig
from src.model.error import errors
from abc import ABC, abstractmethod
from copy import deepcopy


class ICustomerCRUD_DAO(ABC):
    """
    Interface (Port) which declares basic CRUD operations for persisting Customers - needed by `CustomerCRUDController`.

    We can have concrete implementations (Adapters) in the 'persistence' package.

    IMPORTANT! In implementations when you are raising `~src.model.error.errors.ServiceRuntimeError`s please use the appropriate ERRCODE_xxx_FAILED constant as error_code!
    """

    # Implementors SHOULD use these error codes when running into problem
    ERRCODE_UPSERT_FAILED = "customer_db_upsert_failed"
    ERRCODE_READ_FAILED = "customer_db_read_failed"
    ERRCODE_DELETE_FAILED = "customer_db_delete_failed"

    @abstractmethod
    def upsert(self, customer_data: Customer, cntx: ExecutionContext = None) -> None:
        """
        Inserts / Updates the given Customer in persistence.

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def read(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]: 
        """
        Retrieves a Customer from the persistence who's ID is `customer_id` or returns None if not found

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def delete(self, customer_id: str, cntx: ExecutionContext = None) -> None:
        """
        Deletes a specific Customer if exsist

        Might raise:
         * `~src.model.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...


class CustomerCRUDController:
    """
    This controller is responsible for providing CRUD operations for Customers.

    This class is in the core of application business logic! In "Clean architecture" principles actually it is implementing so called "Use cases".

    For persistence purposes it has a dependency on the defined interface `ICustomerCRUD_DAO`
    and you must inject an implementation during construct time.
    """

    def __init__(self, config: ServiceConfig, customer_DAO: ICustomerCRUD_DAO):
        self._LOG: Logger = LoggerFactory.getLogger("service.controller.CustomerCRUDController")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=ServiceConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='customer_DAO', paramValueToCheck=customer_DAO, acceptedTypes=ICustomerCRUD_DAO, loggerToUse=self._LOG)

        self._customer_DAO = customer_DAO


    def create(self, customer_data: Customer, cntx: ExecutionContext = None) -> str:
        """
        Creates a Customer - based on the passed Customer data.

        If the 'id' of the customer not provided then assigns a new one and creates customer that way.
        Returns the 'id' of the newly created Customer.

        In case 'id' is provided with the Customer data (generated server side) and that 'id' is already taken then it is raising
        `~src.model.error.errors.ConstraintViolationError` with code `~src.model.error.errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN`
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("creating Customer: %s", customer_data, **labels)
        preconditions.check_argument(customer_data != None and isinstance(customer_data, Customer), "'customer_data' parameter must be provided and it must be Customer type")
        # we should not modify the passed in object - so take a copy
        customer_data = deepcopy(customer_data)

        # the underlying DAO is upsert based - but now we have a create
        # we must ensure we do not turn accidentally this create operation into an update...
        # so... do we have an inbound customer ID or not?
        if strings.is_blank(customer_data.id):
            # not - let's auto-set ID then and move on
             customer_data.id = ids.generate_uuid()
             self._LOG.debug("'id' was empty - generated new 'id': %s", customer_data.id, **labels)
        else:
            # yes we do - so let's check if still free
            existing_customer: Customer = self._customer_DAO.read(customer_data.id)
            if existing_customer != None:
                # OOps...
                err: str = f"Failed to create Customer - id '{customer_data.id}' already exists"
                self._LOG.error(err, **labels)
                raise errors.ConstraintViolationError(message=err, error_codes={errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN})

        # now version stuff - we must persist with v1
        customer_data.version = 1

        self._customer_DAO.upsert(customer_data = customer_data, cntx = cntx)
        return customer_data.id


    def get(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]:
        """
        Retrieves a Customer belongs to 'customer_id' - if exists. Otherwise None.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving Customer id=%s", customer_id, **labels)

        preconditions.check_argument(strings.is_not_blank(customer_id), "'customer_id' can not be blank")

        customer: Customer = self._customer_DAO.read(customer_id=customer_id, cntx=cntx)

        if customer == None:
            self._LOG.debug("not found", **labels)

        return customer


    def update(self, customer_data: Customer, cntx: ExecutionContext = None):
        """
        Updates an existing Customer to match with the given attributes.
        """
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("updating Customer: %s", customer_data, **labels)

        preconditions.check_argument(customer_data != None and isinstance(customer_data, Customer), "'customer_data' parameter must be provided and it must be Customer type")
        # we should not modify the passed in object - so take a copy
        #customer_data = deepcopy(customer_data)

        # the underlying DAO is upsert based - but now we have an update
        # so to avoid we create the Customer instead of updating an existing we need a read back first
        existing_customer: Customer = self._customer_DAO.read(customer_data.id)
        if existing_customer == None:
            # Oops it does not exist
            err: str = f"Failed to update Customer - id '{customer_data.id}' does not exist"
            self._LOG.error(err, **labels)
            raise errors.ResourceNotFoundError(message=err)

        # so we have the guy!
        # let's check the versions - any optimistic locking problem?
        if existing_customer.version != customer_data.version:
            # Oops it does not work...
            err: str = f"Failed to update Customer - assumed and actual resource versions do not match! Very likely someone else has updated this resource in the meantime - please read it again!"
            self._LOG.error(err, **labels)
            raise errors.OptimisticLockingError(message = err, error_codes = errors.OptimisticLockingError.ERRCODE_VERSION_CONFLICT, assumed_version=customer_data.version, actual_version=existing_customer.version)

        # now, merge in changes to the existing record
        existing_customer.name = customer_data.name
        existing_customer.email = customer_data.email
        # version should be increased
        existing_customer.version = existing_customer.version + 1

        self._customer_DAO.upsert(customer_data = existing_customer, cntx = cntx)


    def delete(self, customer_id: str, cntx: ExecutionContext = None):
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("deleting Customer id=%s", customer_id, **labels)

        # this way we will also log the stuff
        preconditions.check_argument(strings.is_not_blank(customer_id), "'customer_id' can not be blank")

        # we just want to delete someone who exists... idempotency is nice but transparency is favored ;-)
        existing_customer: Customer = self._customer_DAO.read(customer_id)
        if existing_customer == None:
            # Oops it does not exist
            err: str = f"Failed to update Customer - id '{customer_data.id}' does not exist"
            self._LOG.error(err, **labels)
            raise errors.ResourceNotFoundError(message=err)

        self._customer_DAO.delete(customer_id = customer_id)

