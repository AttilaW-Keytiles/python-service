from src.model.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from persistence.sqlite.sqlite_account_dao import SqliteAccountDAO
from src.controller.account_crud import IAccountCRUD_DAO
from src.model.api.generated.banking_api_v1 import Account, AccountStatus
from src.model.error import errors
import os
from copy import deepcopy
import pytest

sqliteConfig: SqliteConfig = SqliteConfig(**{
    "db_file": "local_workfolder/tmp/_sqlite_accountsDAO_test.db",
    "schema_files": {
        "accounts": ["db_schemas/sqlite/schema_accounts.sql"]
    }
})

@pytest.fixture(autouse=True)
def ensureDBIsFlushed() -> None:
    # remove file
    if os.path.exists(sqliteConfig.db_file):
        os.remove(sqliteConfig.db_file)

def createDAO() -> SqliteAccountDAO:
    db: SqliteDB = SqliteDB(config = sqliteConfig)
    # create our DAO on top of it
    dao: SqliteAccountDAO = SqliteAccountDAO(config=sqliteConfig, db=db)
    return dao


def test_SqliteCustomerDAO_happypath_opSequence():
    """This test executes a sequence of operations - to make sure persistence really works high level"""

    # ---- GIVEN

    dao: SqliteAccountDAO = createDAO()

    account_id_1: str = "test-account-1"

    # ---- WHEN
    # we read anything

    rec: Account = dao.read(account_id = account_id_1)

    # ---- THEN

    # we get back no record (DB is empty)
    assert rec is None

    # ---- WHEN
    # let's add a record

    account1: Account = Account(
        id = account_id_1,
        balance = 56.3,
        customerId = "customer-id",
        createdAt = 1234567,
        status = AccountStatus.active,
        version = 16
    )
    dao.upsert(account_data = account1)

    # ---- THEN
    # now we can read it back

    rec: Account = dao.read(account_id = account_id_1)
    assert rec is not None
    assert account1 == rec

    # ---- WHEN
    # now let's modify our account data a bit

    modified_account1: Account = deepcopy(account1)
    modified_account1.customerId += "_mod"
    modified_account1.status = AccountStatus.disabled
    modified_account1.balance = -84.1
    modified_account1.version = 20
    # persist this change
    dao.upsert(account_data = modified_account1)

    # ---- THEN
    # what we read back should be the modified stuff

    rec: Account = dao.read(account_id = account_id_1)
    assert account1 != rec
    assert modified_account1 == rec

