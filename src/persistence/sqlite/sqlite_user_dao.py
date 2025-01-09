from src.api.http.authenticator import IUserProvider
from src.observability.logging import LoggerFactory, Logger
from src.context.contexts import ExecutionContext
from src.model.config.models import SqliteConfig
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.util import dependency_validator, preconditions, strings
from src.model.error import errors
from copy import deepcopy
from src.model.db.models import User

class SqliteUserDAO(IUserProvider):
    """
    SQLite implementation (Adapter) of the `~src.api.http.authenticator.IUserProvider` interface (Port).
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

        schema_files = self.config.schema_files.get("users")
        preconditions.check_argument(schema_files != None and isinstance(schema_files, list), "SqliteConfig error! /schema_files/users entry must be present and it must be a list[str]")

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
                raise errors.ServiceRuntimeError(err, "user_db_schema_creation_failed") from e

        conn.close()

        self._LOG.info("DB schema is generated")


    def _db_row_to_account(self, row) -> User:
         if row == None:
            return None
         return User(
            id = row["id"],
            name = row["name"],
            email = row["email"],
            username = row["username"],
            password = row["password"],
            customer_id = row["customer_id"],
            version = row["version"]
        )

    def get_user_by_username(self, user_name: str, cntx: ExecutionContext) -> User|None:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        self._LOG.debug("reading User username=%s ...", user_name, **labels)

        user: User = None

        conn = self.db.get_connection(cntx = cntx)

        try:
            # this way we will also log the stuff
            preconditions.check_argument(strings.is_not_blank(user_name), "'user_name' can not be blank")

            # we always use params - SQL Injection danger!!
            query = "SELECT * FROM user WHERE username=:user_name"
            cr = conn.cursor()
            params = {
                "user_name": user_name,
            }
            cr.execute(query, params)
            row = cr.fetchone()
            if row != None:
                user = self._db_row_to_account(row)

        except Exception as e:
                err = f"Failed to read User username='{user_name}' due to error: {e}"
                self._LOG.error(err, **labels)
                raise errors.ServiceRuntimeError(err, IUserProvider.ERRCODE_READ_USER_BY_USERNAME_FAILED) from e
        finally:
             conn.close()

        if user == None:
            self._LOG.debug("not found", **labels)

        return user


