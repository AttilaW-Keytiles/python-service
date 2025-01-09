from src.model.config.models import ServiceConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from persistence.sqlite.sqlite_customer_dao import SqliteCustomerDAO
from persistence.sqlite.sqlite_account_dao import SqliteAccountDAO
from src.controller.customer_crud import ICustomerCRUD_DAO
from src.controller.account_crud import AccountCRUDController
from src.model.api.generated.banking_api_v1 import Customer, Account, AccountStatus
from src.context.contexts import ExecutionContext
from src.model.auth.auth_info import AuthInfo
from src.model.auth import roles
from src.model.error import errors
import os
from copy import deepcopy
import pytest

serviceConfig: ServiceConfig = ServiceConfig(**{
    "persistence": {
        "sqlite": {
            "db_file": "local_workfolder/tmp/_sqlite_AccountCRUDController_test.db",
            "schema_files": {
                "customers": ["db_schemas/sqlite/schema_customers.sql"],
                "accounts": ["db_schemas/sqlite/schema_accounts.sql"],
                "transfers": ["db_schemas/sqlite/schema_transfers.sql"]
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


def createController() -> AccountCRUDController:
    # we start from a fresh SqlitDB
    db: SqliteDB = SqliteDB(config = serviceConfig.persistence_config.sqlite_config)
    # create our DAO on top of it
    customerDAO: SqliteCustomerDAO = SqliteCustomerDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    accountDAO: SqliteAccountDAO = SqliteAccountDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    controller: AccountCRUDController = AccountCRUDController(config=serviceConfig, account_DAO=accountDAO, customer_DAO=customerDAO)
    return controller

def getAuthenticatedContext() -> ExecutionContext:
    auth_info = AuthInfo(
        user_id="fake-user-id",
        user_name="fake_guy",
        roles = set()
    )
    # lets add all of them
    for role in roles.AUTH_ROLES.keys():
        auth_info.roles.add(role)

    cntx = ExecutionContext(auth_info=auth_info)
    return cntx


def test_SqliteAccountDAO_happypath_opSequence():
    """This test executes a sequence of CRUD operations - and check the state. Basically it is testing through all methods.
       But, on a happy path so no stressing validation logic"""

    # ---- GIVEN

    controller: AccountCRUDController = createController()
    cntx = getAuthenticatedContext()

    # we need a valid customers
    customer1: Customer = Customer(
        id = "customer_id1",
        name = "customer1_name",
        version = 5
    )
    controller._customer_DAO.upsert(customer1)
    customer2: Customer = Customer(
        id = "customer_id2",
        name = "customer2_name",
        version = 12
    )
    controller._customer_DAO.upsert(customer2)

    account1: Account = Account(
        # would lead to validation error - server side generated so do not send
        #id = "account_id_1",
        balance = 56.3,
        customerId = customer1.id,
        # would lead to validation error - server side generated so do not send
        #createdAt = 1234567,
        #status = AccountStatus.active,
        #version = 16
    )
    account2: Account = Account(
        # would lead to validation error - server side generated so do not send
        #id = "account_id_1",
        balance = 85.1,
        customerId = customer1.id,
        # would lead to validation error - server side generated so do not send
        #createdAt = 1234567,
        status = "disabled",
        #version = 16
    )

    # ---- WHEN
    # let's query into the empty DB

    actualAccountObj: Account = controller.get(account_id = "account_id_1", cntx=cntx)

    # ---- THEN
    # we have no result

    assert actualAccountObj is None

    # ---- WHEN
    # now let's create account1 and account2

    returned_account1_id = controller.create(account_data = account1, cntx=cntx)
    returned_account2_id = controller.create(account_data = account2, cntx=cntx)

    # ---- THEN
    
    # and we should see the guys now
    actualAccountObj: Account = controller.get(account_id = returned_account1_id, cntx=cntx)
    assert actualAccountObj is not None
    # with fields like
    assert returned_account1_id == actualAccountObj.id
    assert 1 == actualAccountObj.version
    assert actualAccountObj.createdAt is not None
    assert AccountStatus.active == actualAccountObj.status
    assert account1.balance == actualAccountObj.balance
    assert account1.customerId == actualAccountObj.customerId

    # ---- WHEN
    # let's modify through the fields

    actualAccountObj.status = AccountStatus.disabled
    actualAccountObj.balance = -84.9
    actualAccountObj.customerId = customer2.id
    controller.update(account_data = actualAccountObj, cntx=cntx)

    # ---- THEN

    updatedActualAccountObj: Account = controller.get(account_id = actualAccountObj.id, cntx=cntx)
    assert updatedActualAccountObj is not None
    # with fields like
    assert actualAccountObj.id == updatedActualAccountObj.id
    assert 2 == updatedActualAccountObj.version
    assert actualAccountObj.status == updatedActualAccountObj.status
    assert actualAccountObj.balance == updatedActualAccountObj.balance
    assert actualAccountObj.customerId == updatedActualAccountObj.customerId
    assert actualAccountObj.createdAt == updatedActualAccountObj.createdAt
    



def _unhappypath_create_helper(accountToSendIn: any, cntx: ExecutionContext) -> dict[str, any]:
    """
    Helper method - to eliminate lots of boilerplate - related to create() stressing
    """

    # ---- GIVEN

    controller: AccountCRUDController = createController()

    # ---- WHEN
    # we invoke the method with what we got

    retValue = None
    errThrown = None
    try:
        retValue = controller.create(accountToSendIn, cntx=cntx)
    except Exception as e:
        errThrown = e

    return {
        'retValue': retValue,
        'errThrown': errThrown
    }


def test_SqliteAccountDAO_unhappypath_create_idProvided():
    """
    'id' always generated server side - so this should fail
    """

    # ---- GIVEN

    controller: AccountCRUDController = createController()
    cntx = getAuthenticatedContext()

    # we need a valid customer
    customer1: Customer = Customer(
        id = "customer_id1",
        name = "customer1_name",
        version = 5
    )
    controller._customer_DAO.upsert(customer1)

    accountToSendIn: Account = Account(
        id = "account_id_1",
        balance = 56.3,
        customerId = customer1.id,
    )

    # ---- WHEN

    results: dict[str, any] = _unhappypath_create_helper(accountToSendIn, cntx=cntx)
    errThrown = results.get('errThrown')
    retValue = results.get('retValue')

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_SHOULD_NOT_BE_PROVIDED)
    assert "account_data.id" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Account" in strForm
    assert "'id' was provided however not expected" in strForm