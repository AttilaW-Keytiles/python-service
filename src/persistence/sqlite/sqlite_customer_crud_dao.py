from src.controller.customer_crud import ICustomerCRUD_DAO
from src.model.api.generated.banking_api_v1 import Customer
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.context.contexts import ExecutionContext
from src.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.util import dependency_validator, preconditions, strings
from src.error import errors

class SqliteCustomerDAO(ICustomerCRUD_DAO):
    """
    SQLite implementation (Adapter) of the `~src.controller.customer_crud.ICustomerCRUD_DAO` interface (Port).
    """

    def __init__(self, config: SqliteConfig = None, db: SqliteDB = None):
        self._LOG: Logger = LoggerFactory.getLogger("service.persistence.SqliteCustomerDAO")

        # validate params
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='config', paramValueToCheck=config, acceptedTypes=SqliteConfig, loggerToUse=self._LOG)
        dependency_validator.ensureGivenAndTypeMatching(targetInstance=self, paramName='db', paramValueToCheck=db, acceptedTypes=SqliteDB, loggerToUse=self._LOG)
        # and store
        self.db: SqliteDB = db
        self.config: SqliteConfig = config

        self._create_db_schema_if_not_exist()


    # This method generates the schema in the DB - if does not exist
    def _create_db_schema_if_not_exist(self) -> None:
        self._LOG.info("generating DB schema - if not exists...")

        schema_files = self.config.schema_files.get("customers")
        preconditions.check_argument(schema_files != None and isinstance(schema_files, list), "SqliteConfig error! /schema_files/customers entry must be present and it must be a list[str]")

        conn = self.db.get_connection()

        for file_path in schema_files:
            try:
                with open(file_path) as f:
                        self._LOG.debug("   executing schema file: %s ...", file_path)
                        script = f.read()
                        cr = conn.cursor()
                        cr.executescript(script)
                        conn.commit()
                        self._LOG.debug("   done!")
            except Exception as e:
                err = f"Failed to execute schema creation file '{file_path}' due to error: {e}"
                self._LOG.error(err)
                raise errors.ServiceRuntimeError(err, "customer_db_schema_creation_failed") from e
            finally:
                 conn.close()


        self._LOG.info("DB schema is generated")

    def upsert(self, customer_data: Customer, cntx: ExecutionContext = None) -> None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("upserting Customer: %s", customer_data, **labels)
        
        conn = self.db.get_connection()

        try:
            # this way we will also log the stuff
            preconditions.check_argument(customer_data != None and isinstance(customer_data, Customer), "'customer_data' parameter must be provided and it must be Customer type")
            preconditions.check_argument(strings.is_not_blank(customer_data.id), "'id' in 'customer_data' Customer record can not be blank")

            # does record already exist?
            # quick solution now... read back
            existing = self.read(customer_data.id, cntx)
            # we choose different query based on result
            # we always use params - SQL Injection danger!!
            query: str
            if existing == None:
                query = "INSERT INTO customer(id, name, email, version) VALUES(:id, :name, :email, :version)"
            else:
                query = "UPDATE customer SET name=:name, email=:email, version=:version WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": customer_data.id,
                "name": customer_data.name,
                "email": customer_data.email,
                "version": customer_data.version
            }
            cr.execute(query, params)
            conn.commit()

        except Exception as e:
                err = f"Failed to insert Customer due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, ICustomerCRUD_DAO.ERRCODE_UPSERT_FAILED) from e
        finally:
             conn.close()


    def read(self, customer_id: str, cntx: ExecutionContext = None) -> Union[Customer|None]:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("reading Customer id=%s ...", customer_id, **labels)

        customer: Customer = None

        conn = self.db.get_connection()

        try:
            # this way we will also log the stuff
            preconditions.check_argument(strings.is_not_blank(customer_id), "'customer_id' can not be blank")

            # we always use params - SQL Injection danger!!
            query = "SELECT id, name, email, version FROM customer WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": customer_id,
            }
            cr.execute(query, params)
            row = cr.fetchone()
            if row != None:
                customer = Customer(
                      id = row["id"],
                      name = row["name"],
                      email = row["email"],
                      version = row["version"],
                 )

        except Exception as e:
                err = f"Failed to read Customer id='{customer_id}' due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, ICustomerCRUD_DAO.ERRCODE_READ_FAILED) from e
        finally:
             conn.close()

        if customer == None:
            self._LOG.debug("not found", **labels)

        return customer


    def delete(self, customer_id: str, cntx: ExecutionContext = None) -> bool:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("deleting Customer id=%s ...", customer_id, **labels)
        
        conn = self.db.get_connection()

        try:
            # this way we will also log the stuff
            preconditions.check_argument(strings.is_not_blank(customer_id), "'customer_id' can not be blank")

            query = "DELETE FROM customer WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": customer_id,
            }
            cr.execute(query, params)
            conn.commit()

        except Exception as e:
                err = f"Failed to delete Customer due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, ICustomerCRUD_DAO.ERRCODE_DELETE_FAILED) from e
        finally:
             conn.close()

