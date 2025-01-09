from src.controller.account_crud import IAccountCRUD_DAO
from src.model.api.generated.banking_api_v1 import Account, AccountStatus
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.context.contexts import ExecutionContext
from src.model.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.util import dependency_validator, preconditions, strings
from src.model.error import errors
from copy import deepcopy

class SqliteAccountDAO(IAccountCRUD_DAO):
    """
    SQLite implementation (Adapter) of the `~src.controller.account_crud.IAccountCRUD_DAO` interface (Port).
    """

    def __init__(self, config: SqliteConfig = None, db: SqliteDB = None):
        self._LOG: Logger = LoggerFactory.getLogger("service.persistence.SqliteAccountDAO")

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

        schema_files = self.config.schema_files.get("accounts")
        preconditions.check_argument(schema_files != None and isinstance(schema_files, list), "SqliteConfig error! /schema_files/accounts entry must be present and it must be a list[str]")

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
                raise errors.ServiceRuntimeError(err, "account_db_schema_creation_failed") from e

        conn.close()

        self._LOG.info("DB schema is generated")


    def upsert(self, account_data: Account, cntx: ExecutionContext = None) -> None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("upserting Account: %s", account_data, **labels)
        
        conn = self.db.get_connection(cntx = cntx)

        try:
            # this way we will also log the stuff
            preconditions.check_argument(account_data != None and isinstance(account_data, Account), "'account_data' parameter must be provided and it must be Account type")
            preconditions.check_argument(strings.is_not_blank(account_data.id), "'id' in 'account_data' Account record can not be blank")

            # does record already exist?
            # quick solution now... read back
            existing = self.read(account_data.id, cntx)
            # we choose different query based on result
            # we always use params - SQL Injection danger!!
            query: str
            if existing == None:
                query = "INSERT INTO account(id, customer_id, balance, created_at_utc, status, version) VALUES(:id, :customer_id, :balance, :created_at_utc, :status, :version)"
            else:
                query = "UPDATE account SET customer_id=:customer_id, balance=:balance, status=:status, version=:version WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": account_data.id,
                "customer_id": account_data.customerId,
                "balance": account_data.balance,
                "created_at_utc": account_data.createdAt,
                "status": account_data.status.value,
                "version": account_data.version
            }
            cr.execute(query, params)
            conn.commit()

        except Exception as e:
                err = f"Failed to insert Account due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, IAccountCRUD_DAO.ERRCODE_UPSERT_FAILED) from e
        finally:
             conn.close()


    def read(self, account_id: str, cntx: ExecutionContext = None) -> Union[Account|None]:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("reading Account id=%s ...", account_id, **labels)

        account: Account = None

        conn = self.db.get_connection(cntx = cntx)

        try:
            # this way we will also log the stuff
            preconditions.check_argument(strings.is_not_blank(account_id), "'account_id' can not be blank")

            # we always use params - SQL Injection danger!!
            query = "SELECT id, customer_id, balance, created_at_utc, status, version FROM account WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": account_id,
            }
            cr.execute(query, params)
            row = cr.fetchone()
            if row != None:
                account = Account(
                      id = row["id"],
                      status = AccountStatus(row["status"]),
                      customerId = row["customer_id"],
                      balance = row["balance"],
                      createdAt = row["created_at_utc"],
                      version = row["version"],
                 )

        except Exception as e:
                err = f"Failed to read Account id='{account_id}' due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, IAccountCRUD_DAO.ERRCODE_READ_FAILED) from e
        finally:
             conn.close()

        if account == None:
            self._LOG.debug("not found", **labels)

        return account


