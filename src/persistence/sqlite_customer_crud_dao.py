from src.controller.customer_crud import ICustomerCRUD_DAO
from src.model.api.generated.banking_api_v1 import Customer
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.context.contexts import ExecutionContext


class SqliteCustomerDAO(ICustomerCRUD_DAO):
    """
    SQLite implementation (Adapter) of the `~src.controller.customer_crud.ICustomerCRUD_DAO` interface (Port).
    """

    def __init__(self, config: dict[str,any]):
        self._LOG: Logger = LoggerFactory.getLogger("service.persistence.SqliteCustomerDAO")

    def upsert(self, customer_data: Customer, cntx: ExecutionContext = None) -> None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("upserting Customer: %s", customer_data, **labels)

    def read(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("reading Customer id=%s ...", customer_id, **labels)
        customer: Customer = None

        if customer == None:
            self._LOG.debug("not found", **labels)

        return customer

    def delete(self, customer_id: str, cntx: ExecutionContext = None) -> None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("deleting Customer id=%s ...", customer_id, **labels)
