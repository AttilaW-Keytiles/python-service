from src.controller.transfer_crud import ITransferCRUD_DAO
from src.model.api.generated.banking_api_v1 import Transfer, TransferStatus
from src.observability.logging import LoggerFactory, Logger
from typing import Union
from src.context.contexts import ExecutionContext
from src.model.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.util import dependency_validator, preconditions, strings
from src.model.error import errors
from copy import deepcopy

class SqliteTransferDAO(ITransferCRUD_DAO):
    """
    SQLite implementation (Adapter) of the `~src.controller.transfer_crud.ITransferCRUD_DAO` interface (Port).
    """

    def __init__(self, config: SqliteConfig = None, db: SqliteDB = None):
        self._LOG: Logger = LoggerFactory.getLogger("service.persistence.SqliteTransferDAO")

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

        schema_files = self.config.schema_files.get("transfers")
        preconditions.check_argument(schema_files != None and isinstance(schema_files, list), "SqliteConfig error! /schema_files/transfers entry must be present and it must be a list[str]")

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
                raise errors.ServiceRuntimeError(err, "transfer_db_schema_creation_failed") from e

        conn.close()

        self._LOG.info("DB schema is generated")


    def insert(self, transfer_data: Transfer, cntx: ExecutionContext = None) -> None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("upserting Transfer: %s", transfer_data, **labels)

        # does record already exist?
        # quick solution now... read back
        existing = self.read(transfer_data.id, cntx)
        if existing != None:
            # Oops...
            err: str = f"Failed to insert Transfer - already exists"
            self._LOG.error(err, **labels)
            raise errors.ConstraintViolationError(message=err, error_codes={errors.ConstraintViolationError.ERRCODE_ID_ALREADY_TAKEN})

        conn = self.db.get_connection()

        try:
            # this way we will also log the stuff
            preconditions.check_argument(transfer_data != None and isinstance(transfer_data, Transfer), "'transfer_data' parameter must be provided and it must be Transfer type")
            preconditions.check_argument(strings.is_not_blank(transfer_data.id), "'id' in 'transfer_data' Transfer record can not be blank")

            query = "INSERT INTO transfer(id, amount, src_account_id, dst_account_id, created_at_utc, created_by, status) VALUES(:id, :amount, :src_account_id, :dst_account_id, :created_at_utc, :created_by, :status)"
            cr = conn.cursor()
            params = {
                "id": transfer_data.id,
                "amount": transfer_data.amount,
                "src_account_id": transfer_data.sourceAccountId,
                "dst_account_id": transfer_data.destinationAccountId,
                "created_by": transfer_data.createdBy,
                "created_at_utc": transfer_data.createdAt,
                "status": transfer_data.status.value
            }
            cr.execute(query, params)
            conn.commit()

        except Exception as e:
            err = f"Failed to insert Transfer due to error: {e}"
            self._LOG.error(err, **labels)
            raise errors.ServiceRuntimeError(err, ITransferCRUD_DAO.ERRCODE_UPSERT_FAILED) from e
        finally:
             conn.close()


    def read(self, transfer_id: str, cntx: ExecutionContext = None) -> Union[Transfer|None]:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("reading Transfer id=%s ...", transfer_id, **labels)

        transfer: Transfer = None

        conn = self.db.get_connection()

        try:
            # this way we will also log the stuff
            preconditions.check_argument(strings.is_not_blank(transfer_id), "'transfer_id' can not be blank")

            # we always use params - SQL Injection danger!!
            query = "SELECT id, amount, src_account_id, dst_account_id, created_at_utc, created_by, status FROM transfer WHERE id=:id"
            cr = conn.cursor()
            params = {
                "id": transfer_id,
            }
            cr.execute(query, params)
            row = cr.fetchone()
            if row != None:
                transfer = Transfer(
                      id = row["id"],
                      status = TransferStatus(row["status"]),
                      amount = row["amount"],
                      sourceAccountId = row["src_account_id"],
                      destinationAccountId = row["dst_account_id"],
                      createdBy = row["created_by"],
                      createdAt = row["created_at_utc"],
                 )

        except Exception as e:
                err = f"Failed to read Transfer id='{transfer_id}' due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, ITransferCRUD_DAO.ERRCODE_READ_FAILED) from e
        finally:
             conn.close()

        if transfer == None:
            self._LOG.debug("not found", **labels)

        return transfer


