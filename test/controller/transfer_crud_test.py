from src.model.config.models import ServiceConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from persistence.sqlite.sqlite_customer_dao import SqliteCustomerDAO
from persistence.sqlite.sqlite_account_dao import SqliteAccountDAO
from persistence.sqlite.sqlite_transfer_dao import SqliteTransferDAO
from src.controller.transfer_crud import TransferCRUDController
from src.model.api.generated.banking_api_v1 import Customer, Account, AccountStatus, Transfer, TransferStatus
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
            "db_file": "local_workfolder/tmp/_sqlite_TransferCRUDController_test.db",
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


def createController() -> TransferCRUDController:
    # we need connection
    db: SqliteDB = SqliteDB(config = serviceConfig.persistence_config.sqlite_config)
    # create our DAOs on top of it
    accountDAO: SqliteAccountDAO = SqliteAccountDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    transferDAO: SqliteTransferDAO = SqliteTransferDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    controller: TransferCRUDController = TransferCRUDController(config=serviceConfig, account_DAO=accountDAO, transfer_DAO=transferDAO)
    return controller

def getAuthenticatedContext() -> ExecutionContext:
    auth_info = AuthInfo(
        user_id="fake-user-id",
        user_name="fake_guy",
        roles = roles.AUTH_ROLES.keys
    )
    cntx = ExecutionContext(auth_info=auth_info)
    return cntx


# we need a few accounts
account1: Account = Account(
    id = "account_id_1",
    balance = 56.3,
    customerId = "customer1.id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 16
)
account2: Account = Account(
    id = "account_id_2",
    balance = 18.6,
    customerId = "customer2.id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 5
)
account3: Account = Account(
    id = "account_id_3",
    balance = 241.1,
    customerId = "customer3.id",
    createdAt = 1234567,
    status = AccountStatus.disabled,
    version = 5
)

def someTestAccountsExist(controller: TransferCRUDController):
    controller._account_DAO.upsert(account_data=account1)
    controller._account_DAO.upsert(account_data=account2)
    controller._account_DAO.upsert(account_data=account3)


def test_SqliteAccountDAO_happypath_opSequence():
    """This test executes a sequence of CRUD operations - and check the state. Basically it is testing through all methods.
       But, on a happy path so no stressing validation logic"""

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    # ---- WHEN
    # let's query into the empty DB

    actualTransferObj: Transfer = controller.get(transfer_id = "transfer-1-id", cntx=cntx)

    # ---- THEN
    # we have no result

    assert actualTransferObj is None

    # ---- WHEN
    # now let's create a transfer - btw account1 -> account2

    transfer1: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = account2.id,
    )
    controller.create(transfer_data = transfer1, cntx=cntx)

    # ---- THEN
    
    # we should see the Transfer - as it should have been succeeded
    actualTransferObj: Transfer = controller.get(transfer_id = transfer1.id, cntx=cntx)
    assert actualTransferObj is not None
    # with fields like
    assert transfer1.id == actualTransferObj.id
    assert TransferStatus.settled == actualTransferObj.status
    assert transfer1.sourceAccountId == actualTransferObj.sourceAccountId
    assert transfer1.destinationAccountId == actualTransferObj.destinationAccountId
    assert transfer1.amount == actualTransferObj.amount
    assert actualTransferObj.createdAt is not None

    # the accounts balance should be correct
    actualAccount1Obj = controller._account_DAO.read(account_id = account1.id)
    actualAccount2Obj = controller._account_DAO.read(account_id = account2.id)
    assert 46.3 == actualAccount1Obj.balance
    assert 28.6 == actualAccount2Obj.balance


def _unhappypath_create_helper(transferToSendIn: any, cntx: ExecutionContext) -> Exception:
    """
    Helper method - to eliminate lots of boilerplate - related to create() stressing
    """

    # ---- GIVEN

    controller: TransferCRUDController = createController()

    # ---- WHEN
    # we invoke the method with what we got

    errThrown = None
    try:
        controller.create(transferToSendIn, cntx=cntx)
    except Exception as e:
        errThrown = e

    return errThrown


def test_SqliteAccountDAO_unhappypath_create_emptyIdProvided():
    """
    'id' must be always provided client side
    """

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = account2.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_MISSING_MANDATORY)
    assert "transfer_data.id" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "'id' is mandatory" in strForm

def test_SqliteAccountDAO_unhappypath_create_invalidSrcAccountProvided():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = "does-not-exist",
        destinationAccountId = account2.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_INVALID_VALUE)
    assert "transfer_data.sourceAccountId" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "this account does not exist" in strForm

def test_SqliteAccountDAO_unhappypath_create_invalidDstAccountProvided():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = "does-not-exist",
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_INVALID_VALUE)
    assert "transfer_data.destinationAccountId" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "this account does not exist" in strForm

def test_SqliteAccountDAO_unhappypath_create_sameSrcAndDstAccountProvided():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = account1.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_INVALID_VALUE)
    assert "transfer_data.destinationAccountId" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "can not be the same" in strForm

def test_SqliteAccountDAO_unhappypath_create_invalid0Amount():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 0,
        sourceAccountId = account1.id,
        destinationAccountId = account2.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ValidationError)
    # the error code should conform the expectation...
    assert errThrown.has_error(errors.ValidationError.ERRCODE_INVALID_VALUE)
    assert "transfer_data.amount" == errThrown.place_name
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "'amount' must be >0" in strForm

def test_SqliteAccountDAO_unhappypath_create_disabledSrcAccountProvided():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account3.id,
        destinationAccountId = account2.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ConstraintViolationError)
    # the error code should conform the expectation...
    assert errThrown.has_error("src_account_invalid_status")
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "status is not Active" in strForm

def test_SqliteAccountDAO_unhappypath_create_disabledDstAccountProvided():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = account3.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ConstraintViolationError)
    # the error code should conform the expectation...
    assert errThrown.has_error("dst_account_invalid_status")
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "status is not Active" in strForm    

def test_SqliteAccountDAO_unhappypath_create_notEnoughMoney():

    # ---- GIVEN

    controller: TransferCRUDController = createController()
    cntx = getAuthenticatedContext()
    someTestAccountsExist(controller = controller)

    transferToSendIn: Transfer = Transfer(
        id = "transfer-1-id",
        amount = account1.balance + 0.1,
        sourceAccountId = account1.id,
        destinationAccountId = account2.id,
    )

    # ---- WHEN

    errThrown = _unhappypath_create_helper(transferToSendIn, cntx=cntx)

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ConstraintViolationError)
    # the error code should conform the expectation...
    assert errThrown.has_error("not_enough_balance")
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to create Transfer" in strForm
    assert "does not have enough money" in strForm        