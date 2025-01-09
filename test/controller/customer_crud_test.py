from src.model.config.models import ServiceConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from persistence.sqlite.sqlite_customer_dao import SqliteCustomerDAO
from src.controller.customer_crud import ICustomerCRUD_DAO, CustomerCRUDController
from src.model.api.generated.banking_api_v1 import Customer
from src.model.error import errors
import os
from copy import deepcopy
import pytest
from src.context.contexts import ExecutionContext
from src.model.auth.auth_info import AuthInfo
from src.model.auth import roles

serviceConfig: ServiceConfig = ServiceConfig(**{
    "persistence": {
        "sqlite": {
            "db_file": "local_workfolder/tmp/_sqlite_CustomerCRUDController_test.db",
            "schema_files": {
                "customers": ["db_schemas/sqlite/schema_customers.sql"]
            }
        }
    }
})

@pytest.fixture(autouse=True)
def ensureDBIsFlushed() -> None:
    # remove file
    db_file = serviceConfig.persistence_config.sqlite_config.db_file
    if os.path.exists(db_file):
        os.remove(db_file)


def createController() -> CustomerCRUDController:
    # we start from a fresh SqlitDB
    db: SqliteDB = SqliteDB(config = serviceConfig.persistence_config.sqlite_config)
    # create our DAO on top of it
    dao: SqliteCustomerDAO = SqliteCustomerDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    controller: CustomerCRUDController = CustomerCRUDController(config=serviceConfig, customer_DAO=dao)
    return controller

def getAuthenticatedContext() -> ExecutionContext:
    auth_info = AuthInfo(
        user_id="fake-user-id",
        user_name="fake_guy",
        roles = roles.AUTH_ROLES.keys
    )
    cntx = ExecutionContext(auth_info=auth_info)
    return cntx


def test_SqliteCustomerDAO_happypath_opSequence():
    """This test executes a sequence of CRUD operations - and check the state. Basically it is testing through all methods.
       But, on a happy path so no stressing validation logic"""

    # ---- GIVEN

    controller: CustomerCRUDController = createController()
    cntx = getAuthenticatedContext()

    customer_id1: str = "test-customer-1"

    customer1: Customer = Customer(
        id = customer_id1,
        name = "customer1_name",
        email = "customer1_email",
        version = 0
    )    
    customer2: Customer = Customer(
        # we do not assign 'id' to this guy now - controller should do that
        #id = customer_id2,
        name = "customer2_name",
        email = "customer2_email",
        # neither version
        #version = 0
    )    

    # ---- WHEN
    # let's query into the empty DB

    actualCustomerObj: Customer = controller.get(customer_id = customer_id1, cntx=cntx)

    # ---- THEN
    # we have no result

    assert actualCustomerObj is None

    # ---- WHEN
    # now let's create customer1

    returned_id = controller.create(customer_data = customer1, cntx=cntx)

    # ---- THEN
    
    # returned id should be the same
    assert customer_id1 == returned_id

    # and we should see the guy now
    actualCustomerObj: Customer = controller.get(customer_id = customer_id1, cntx=cntx)
    assert actualCustomerObj is not None
    # version should be set to 1
    # apart from that all other attributes should match with the original record
    expectedObj = deepcopy(customer1)
    expectedObj.version = 1
    assert expectedObj == actualCustomerObj

    # ---- WHEN
    # now let's test auto-id assigment
    # let's create a customer who does not have assigned id (it also does not have version by the way)
    returned_id = controller.create(customer_data = customer2, cntx=cntx)

    # ---- THEN
    
    # returned id should be the there first of all
    assert returned_id is not None

    # and we should see the guy now - if query back
    actualCustomerObj: Customer = controller.get(customer_id = returned_id, cntx=cntx)
    assert actualCustomerObj is not None
    # version should be set to 1
    # apart from that all other attributes should match with the original record
    expectedObj = deepcopy(customer2)
    expectedObj.id = returned_id
    expectedObj.version = 1
    assert expectedObj == actualCustomerObj

    # ---- WHEN
    # time to test update

    



def _unhappypath_create_helper(customerToSendIn: any, cntx: ExecutionContext) -> dict[str, any]:
    """
    Helper method - to eliminate lots of boilerplate - related to create() stressing
    """

    # ---- GIVEN

    controller: CustomerCRUDController = createController()

    # ---- WHEN
    # we invoke the method with what we got

    retValue = None
    errThrown = None
    try:
        retValue = controller.create(customerToSendIn, cntx=cntx)
    except Exception as e:
        errThrown = e

    return {
        'retValue': retValue,
        'errThrown': errThrown
    }


def test_SqliteCustomerDAO_unhappypath_create_duplicatedIds():
    """
    When 'id' is assigned client side it can happen caller tries to create the same Customer again - with same 'id'.
    This should be rejected and proper error being raised - this test is testing this
    """

    # ---- GIVEN

    cntx = getAuthenticatedContext()

    customerToSendIn: Customer = Customer(
        id = "customer1_id",
        name = "customer1_name",
        email = "customer1_email",
    )

    # ---- WHEN

    results: dict[str, any] = _unhappypath_create_helper(customerToSendIn, cntx=cntx)
    errThrown = results.get('errThrown')
    retValue = results.get('retValue')

    # ---- THEN
    # so far this should be ok - no error, id returned

    assert errThrown is None
    assert customerToSendIn.id == retValue

    # ---- WHEN
    # ... but if we try to recreate same again...

    results: dict[str, any] = _unhappypath_create_helper(customerToSendIn, cntx=cntx)
    errThrown = results.get('errThrown')
    retValue = results.get('retValue')

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ConstraintViolationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Customer" in strForm