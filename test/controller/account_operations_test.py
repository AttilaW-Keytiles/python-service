from src.model.config.models import ServiceConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from persistence.sqlite.sqlite_transfer_dao import SqliteTransferDAO
from persistence.sqlite.sqlite_account_dao import SqliteAccountDAO
from persistence.sqlite.sqlite_customer_dao import SqliteCustomerDAO
from src.controller.account_operations import AccountOperationsController
from src.model.api.generated.banking_api_v1 import Customer, Account, AccountStatus, Transfer, TransferDirection, TransferStatus
from src.model.error import errors
import os
from copy import deepcopy
import pytest

serviceConfig: ServiceConfig = ServiceConfig(**{
    "persistence": {
        "sqlite": {
            "db_file": "local_workfolder/tmp/_sqlite_AccountOperationsController_test.db",
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


def createTransferDAO() -> SqliteTransferDAO:
    db: SqliteDB = SqliteDB(config = serviceConfig.persistence_config.sqlite_config)
    # create our DAOs on top of it
    transferDAO: SqliteTransferDAO = SqliteTransferDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    return transferDAO

def createController() -> AccountOperationsController:
    db: SqliteDB = SqliteDB(config = serviceConfig.persistence_config.sqlite_config)
    # create our DAOs on top of it
    accountDAO: SqliteAccountDAO = SqliteAccountDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    customerDAO: SqliteCustomerDAO = SqliteCustomerDAO(config=serviceConfig.persistence_config.sqlite_config, db=db)
    controller: AccountOperationsController = AccountOperationsController(config=serviceConfig, account_ops_DAO=accountDAO, account_crud_DAO=accountDAO, customer_crud_DAO=customerDAO)
    return controller


# we need a few accounts
account1: Account = Account(
    id = "account_id_1",
    balance = 56.3,
    customerId = "customer1-id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 16
)
account2: Account = Account(
    id = "account_id_2",
    balance = 18.6,
    customerId = "customer2-id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 5
)
account3: Account = Account(
    id = "account_id_3",
    balance = 241.1,
    customerId = "customer2-id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 5
)
account4: Account = Account(
    id = "account_id_4",
    balance = 78.1,
    customerId = "customer2-id",
    createdAt = 1234567,
    status = AccountStatus.active,
    version = 5
)
def someTestDataExist(controller: AccountOperationsController):
    controller._account_crud_DAO.upsert(account_data=account1)
    controller._account_crud_DAO.upsert(account_data=account2)
    controller._account_crud_DAO.upsert(account_data=account3)
    controller._account_crud_DAO.upsert(account_data=account4)



def test_SqliteAccountDAO_happypath_getAccountTransfers():
    """Testing the Transfer listing capabilities - happy way"""

    # ---- GIVEN

    transferDAO: SqliteTransferDAO = createTransferDAO()
    controller: AccountOperationsController = createController()
    someTestDataExist(controller=controller)

    # NOTE! createdAt times are in this order!!

    transfer_acc1_acc2: Transfer = Transfer(
        id = "transfer-1-id",
        amount = 10,
        sourceAccountId = account1.id,
        destinationAccountId = account2.id,
        createdAt = 100,
        createdBy = "irrelevant",
        status = TransferStatus.settled
    )
    transferDAO.insert(transfer_data=transfer_acc1_acc2)

    transfer_acc1_acc3: Transfer = Transfer(
        id = "transfer-2-id",
        amount = 5.3,
        sourceAccountId = account1.id,
        destinationAccountId = account3.id,
        createdAt = 200,
        createdBy = "irrelevant",
        status = TransferStatus.settled
    )
    transferDAO.insert(transfer_data=transfer_acc1_acc3)

    transfer_acc3_acc1: Transfer = Transfer(
        id = "transfer-3-id",
        amount = 12.1,
        sourceAccountId = account3.id,
        destinationAccountId = account1.id,
        createdAt = 300,
        createdBy = "irrelevant",
        status = TransferStatus.settled
    )
    transferDAO.insert(transfer_data=transfer_acc3_acc1)

    # ---- WHEN
    # first query ALL stuff happened on acc1

    transfers: list[Transfer] = controller.get_account_transfers(account_id = account1.id, direction = TransferDirection.all)

    # ---- THEN

    # do not forget: it should be ordered by time - desc!
    expectedList = [transfer_acc3_acc1, transfer_acc1_acc3, transfer_acc1_acc2]
    assert expectedList == transfers

    # ---- WHEN
    # now outbound only happened on acc1

    transfers: list[Transfer] = controller.get_account_transfers(account_id = account1.id, direction = TransferDirection.outgoing)

    # ---- THEN

    # do not forget: it should be ordered by time - desc!
    expectedList = [transfer_acc1_acc3, transfer_acc1_acc2]
    assert expectedList == transfers

    # ---- WHEN
    # now inbound only happened on acc1

    transfers: list[Transfer] = controller.get_account_transfers(account_id = account1.id, direction = TransferDirection.incoming)

    # ---- THEN

    # do not forget: it should be ordered by time - desc!
    expectedList = [transfer_acc3_acc1]
    assert expectedList == transfers

    # ---- WHEN
    # finally, some empty list returning...
    # we have no outbound Transfers from acc2

    transfers: list[Transfer] = controller.get_account_transfers(account_id = account2.id, direction = TransferDirection.outgoing)

    # ---- THEN

    expectedList = []
    assert expectedList == transfers


def _unhappypath_getAccountTransfers_helper(account_id: any) -> dict[str, any]:
    """
    Helper method - to eliminate lots of boilerplate - related to create() stressing
    """

    # ---- GIVEN

    controller: AccountOperationsController = createController()

    # ---- WHEN
    # we invoke the method with what we got

    retValue = None
    errThrown = None
    try:
        retValue = controller.get_account_transfers(account_id)
    except Exception as e:
        errThrown = e

    return {
        'retValue': retValue,
        'errThrown': errThrown
    }


def test_SqliteAccountDAO_unhappypath_getAccountTransfersOnNonExistingAccount():
    """
    'id' always generated server side - so this should fail
    """

    # ---- GIVEN

    controller: AccountOperationsController = createController()

    # ---- WHEN

    acc_id = "acc-not-exist"
    results: dict[str, any] = _unhappypath_getAccountTransfers_helper(account_id=acc_id)
    errThrown = results.get('errThrown')
    retValue = results.get('retValue')

    # ---- THEN
    # now we see problems...

    assert errThrown is not None
    assert isinstance(errThrown, errors.ResourceNotFoundError)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to retrieve Transfers for Account" in strForm
    assert f"Account id '{acc_id}' does not exist" in strForm


def test_SqliteAccountDAO_happypath_getCustomerAccounts():
    """Testing the Account listing capabilities - happy way"""

    # ---- GIVEN

    controller: AccountOperationsController = createController()
    someTestDataExist(controller=controller)

    # we need the customer to make test happy
    customer1: Customer = Customer(
        id = "customer1-id",
        name = "customer1_name",
        version = 5
    )
    controller._customer_crud_DAO.upsert(customer1)
    customer2: Customer = Customer(
        id = "customer2-id",
        name = "customer2_name",
        version = 5
    )
    controller._customer_crud_DAO.upsert(customer2)       

    # ---- WHEN

    accounts: list[Account] = controller.get_customer_accounts(customer_id=customer1.id)

    # ---- THEN

    # Note: accounts returned ordered by account-id
    expectedList = [account1]
    assert expectedList == accounts

    # ---- WHEN

    accounts: list[Account] = controller.get_customer_accounts(customer_id=customer2.id)

    # ---- THEN

    # Note: accounts returned ordered by account-id - could have been used Sets? ...
    expectedList = [account2, account3, account4]
    assert expectedList == accounts

