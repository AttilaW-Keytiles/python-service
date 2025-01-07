from src.model.api.generated.banking_api_v1 import Customer
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.util import dependency_validator, preconditions, strings, ids
from src.context.contexts import ExecutionContext
from abc import ABC, abstractmethod


class ICustomerCRUD_DAO(ABC):
    """
    Interface (Port) which declares basic CRUD operations for persisting Customers - needed by `CustomerCRUDController`.

    We can have concrete implementations (Adapters) in the 'persistence' package.

    IMPORTANT! In implementations when you are raising `~src.error.errors.ServiceRuntimeError`s please use the appropriate ERRCODE_xxx_FAILED constant as error_code!
    """

    ERRCODE_UPSERT_FAILED = "customer_db_upsert_failed"
    ERRCODE_READ_FAILED = "customer_db_read_failed"
    ERRCODE_DELETE_FAILED = "customer_db_delete_failed"

    @abstractmethod
    def upsert(self, customer_data: Customer, cntx: ExecutionContext = None) -> None:
        """
        Inserts / Updates the given Customer in persistence.

        Might raise:
         * `~src.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def read(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]: 
        """
        Retrieves a Customer from the persistence who's ID is `customer_id` or returns None if not found

        Might raise:
         * `~src.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...

    @abstractmethod
    def delete(self, customer_id: str, cntx: ExecutionContext = None) -> None:
        """
        Deletes a specific Customer if exsist

        Might raise:
         * `~src.error.errors.ServiceRuntimeError` in case of any other unexpected stuff has happened.
        """
        ...


class CustomerCRUDController:
    """
    This controller is responsible for providing CRUD operations for Customers.

    For persistence purposes it has a dependency on the defined interface `ICustomerCRUD_DAO`
    and you must inject an implementation during construct time.
    """

    _customer_DAO: ICustomerCRUD_DAO

    def __init__(self, config: dict[str, any], customer_DAO: ICustomerCRUD_DAO):
        self._LOG: Logger = LoggerFactory.getLogger("service.controller.CustomerCRUDController")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='customer_DAO', paramValueToCheck=customer_DAO, acceptedTypes=ICustomerCRUD_DAO, loggerToUse=self._LOG)

        self._customer_DAO = customer_DAO


    def create(self, customer_data: Customer, cntx: ExecutionContext = None) -> str:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("creating Customer: %s", customer_data, **labels)
        preconditions.check_argument(customer_data != None, "'customer_data' can not be None")

        # let's auto-set ID if not provided
        if strings.isBlank(customer_data.id):
             customer_data.id = ids.generate_uuid()
             self._LOG.debug("'id' was empty - generated new 'id': %s", customer_data.id, **labels)

        self._customer_DAO.upsert(customer_data = customer_data, cntx = cntx)
        return customer_data.id


    def get(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("retrieving Customer id=%s", customer_id, **labels)

        customer: Customer = self._customer_DAO.read(customer_id=customer_id, cntx=cntx)

        if customer == None:
            self._LOG.debug("not found", **labels)

        return customer


    def update(self, customer_data: Customer, cntx: ExecutionContext = None):
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("updating Customer: %s", customer_data, **labels)

        preconditions.check_argument(customer_data != None, "'customer_data' can not be None")

        self._customer_DAO.upsert(customer_data = customer_data, cntx = cntx)


    def delete(self, customer_id: str, cntx: ExecutionContext = None):
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("deleting Customer id=%s", customer_id, **labels)
