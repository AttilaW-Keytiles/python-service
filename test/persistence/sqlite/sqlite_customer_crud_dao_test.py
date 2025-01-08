from src.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.persistence.sqlite.sqlite_customer_crud_dao import SqliteCustomerDAO
from src.controller.customer_crud import ICustomerCRUD_DAO
from src.model.api.generated.banking_api_v1 import Customer
from src.model.error import errors
import os
from copy import deepcopy
import pytest

sqliteConfig: SqliteConfig = SqliteConfig(**{
    "db_file": "local_workfolder/tmp/_sqlite_customerDAO_test.db",
    "schema_files": {"customers": ["db_schemas/sqlite/schema_customers.sql"]}
})

@pytest.fixture(autouse=True)
def ensureDBIsFlushed() -> None:
    # remove file
    if os.path.exists(sqliteConfig.db_file):
        os.remove(sqliteConfig.db_file)

def createDAO() -> SqliteCustomerDAO:
    db: SqliteDB = SqliteDB(config = sqliteConfig)
    # create our DAO on top of it
    dao: SqliteCustomerDAO = SqliteCustomerDAO(config=sqliteConfig, db=db)
    return dao


def test_SqliteCustomerDAO_happypath_opSequence():
    """This test executes a sequence of upsert, read and finally delete operations - to make sure persistence really works high level"""

    # ---- GIVEN

    dao: SqliteCustomerDAO = createDAO()

    customer_id1: str = "test-customer-1"

    # ---- WHEN
    # we read anything

    rec: Customer = dao.read(customer_id = customer_id1)

    # ---- THEN

    # we get back no record (DB is empty)
    assert None == rec

    # ---- WHEN
    # let's add a record

    customer1: Customer = Customer(
        id = customer_id1,
        name = "customer1_name",
        email = "customer1_email",
        version = 16
    )
    dao.upsert(customer_data = customer1)

    # ---- THEN
    # now we can read it back

    rec: Customer = dao.read(customer_id = customer_id1)
    assert rec != None
    assert rec == customer1

    # ---- WHEN
    # now let's modify our customer data a bit

    modified_customer1 = deepcopy(customer1)
    modified_customer1.name += "_mod"
    modified_customer1.email += "_mod"
    modified_customer1.version = 20
    # persist this change
    dao.upsert(customer_data = modified_customer1)

    # ---- THEN
    # what we read back should be the modified stuff

    rec: Customer = dao.read(customer_id = customer_id1)
    assert rec != customer1
    assert rec == modified_customer1

    # ---- WHEN
    # and finally let's delete this record

    dao.delete(customer_id = customer_id1)

    # ---- THEN
    # we get back no record again - its gone
    rec: Customer = dao.read(customer_id = customer_id1)
    assert rec == None

    # ---- WHEN
    # a repeated delete this record ...

    dao.delete(customer_id = customer_id1)

    # ---- THEN
    # should not make any difference - delete is idempontent basically

    rec: Customer = dao.read(customer_id = customer_id1)
    assert rec == None



def _unhappypath_upsert_helper(customerToSendIn: any) -> Exception:
    """
    Helper method - to eliminate lots of boilerplate - related to upsert() stressing
    """

    # ---- GIVEN

    dao: SqliteCustomerDAO = createDAO()

    # ---- WHEN
    # we invoke the method with what we got

    errThrown = None
    try:
        dao.upsert(customerToSendIn)
    except Exception as e:
        errThrown = e

    return errThrown


def test_SqliteCustomerDAO_unhappypath_upsert_wrongInputType():
    """
    This test is sending stressing the upsert() method - it sends in totally invalid param instead of Customer object.
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

    # ---- GIVEN

    customerToSendIn = "just a string"

    # ---- WHEN

    errThrown = _unhappypath_upsert_helper(customerToSendIn)

    # ---- THEN

    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_UPSERT_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to insert Customer" in strForm
    assert "'customer_data' parameter must be provided and it must be Customer type" in strForm


def test_SqliteCustomerDAO_unhappypath_upsert_missingCurstomerId():
    """
    This test is sending stressing the upsert() method - now Customer object is sent in but customer_id is not given in the record.
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    customerToSendIn: Customer = Customer(
        # let's do not add this at all
        #id = "customer_id1",
        name = "customer1_name",
        email = "customer1_email",
        version = 16
    ) 

    # ---- WHEN

    errThrown = _unhappypath_upsert_helper(customerToSendIn)

    # ---- THEN

    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_UPSERT_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to insert Customer" in strForm
    assert "'id' in 'customer_data' Customer record can not be blank" in strForm


def test_SqliteCustomerDAO_unhappypath_upsert_emptyCurstomerId():
    """
    This test is sending stressing the upsert() method - now Customer object is sent in but customer_id is empty string.
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    customerToSendIn: Customer = Customer(
        # let's make it empty
        id = "  ",
        name = "customer1_name",
        email = "customer1_email",
        version = 16
    ) 

    # ---- WHEN

    errThrown = _unhappypath_upsert_helper(customerToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_UPSERT_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to insert Customer" in strForm
    assert "'id' in 'customer_data' Customer record can not be blank" in strForm


def _unhappypath_read_helper(customerIdToSendIn: any) -> Exception:
    """
    Helper method - to eliminate lots of boilerplate - related to read() stressing
    """

    # ---- GIVEN

    dao: SqliteCustomerDAO = createDAO()

    # ---- WHEN
    # we invoke the method with what we got

    errThrown = None
    try:
        dao.read(customerIdToSendIn)
    except Exception as e:
        errThrown = e

    return errThrown


def test_SqliteCustomerDAO_unhappypath_read_wrongInputType():
    """
    This test is stressing the read() method - it sends in totally invalid param instead of customerId.
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = 1234

    # ---- WHEN

    errThrown = _unhappypath_read_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_READ_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to read Customer" in strForm
    assert "input parameter must be string" in strForm    


def test_SqliteCustomerDAO_unhappypath_read_NoneCustomerId():
    """
    This test is stressing the read() method - it sends in None as customerId
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = None

    # ---- WHEN

    errThrown = _unhappypath_read_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_READ_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to read Customer" in strForm
    assert "'customer_id' can not be blank" in strForm


def test_SqliteCustomerDAO_unhappypath_read_emptyCustomerId():
    """
    This test is stressing the read() method - it sends in empty string as customerId
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = "  \t"

    # ---- WHEN

    errThrown = _unhappypath_read_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_READ_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to read Customer" in strForm
    assert "'customer_id' can not be blank" in strForm


def _unhappypath_delete_helper(customerIdToSendIn: any) -> Exception:
    """
    Helper method - to eliminate lots of boilerplate - related to delete() stressing
    """

    # ---- GIVEN

    dao: SqliteCustomerDAO = createDAO()

    # ---- WHEN
    # we invoke the method with what we got

    errThrown = None
    try:
        dao.delete(customerIdToSendIn)
    except Exception as e:
        errThrown = e

    return errThrown


def test_SqliteCustomerDAO_unhappypath_delete_wrongInputType():
    """
    This test is stressing the delete() method - it sends in totally invalid param instead of customerId.
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = 1234

    # ---- WHEN

    errThrown = _unhappypath_delete_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_DELETE_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to delete Customer" in strForm
    assert "input parameter must be string" in strForm    


def test_SqliteCustomerDAO_unhappypath_delete_NoneCustomerId():
    """
    This test is stressing the delete() method - it sends in None as customerId
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = None

    # ---- WHEN

    errThrown = _unhappypath_delete_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_DELETE_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to delete Customer" in strForm
    assert "'customer_id' can not be blank" in strForm


def test_SqliteCustomerDAO_unhappypath_delete_emptyCustomerId():
    """
    This test is stressing the delete() method - it sends in empty string as customerId
    It should throw a meaningful exception. If one logs that out it tells pretty good the problem.
    """

   # ---- GIVEN

    # send int instead of string
    customerIdToSendIn = "  \t"

    # ---- WHEN

    errThrown = _unhappypath_delete_helper(customerIdToSendIn)

    # ---- THEN
    
    assert errThrown != None
    assert isinstance(errThrown, errors.ServiceRuntimeError)
    # the error code should conform the expectation...
    assert errThrown.has_error(ICustomerCRUD_DAO.ERRCODE_DELETE_FAILED)
    # and message should be meaningful - in String converted form! (as log will do exactly this)
    strForm = str(errThrown)
    assert "Failed to delete Customer" in strForm
    assert "'customer_id' can not be blank" in strForm