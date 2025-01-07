from src.config.models import SqliteConfig
from src.observability.logging import LoggerFactory, Logger
from src.context.contexts import ExecutionContext
from src.error import errors
import sqlite3
from src.util import preconditions

class SqliteDB:

    def __init__(self, config: SqliteConfig = None):
        self._LOG: Logger = LoggerFactory.getLogger("service.persistence.SqliteDB")
        self._LOG.info("will provide connections to db file: %s ...", config.db_file)

        # we have problems here for now with sharing stuff... not time now to fix this so until that let's avoid!
        preconditions.check_argument(config.db_file != ":memory:", "Oops! Sorry, memory mode does not work yet...")

        self.config = config
        """The cofing we use"""
        self.is_closed = False
        """Tells if this connection is still there or already closed"""

    def get_connection(self, cntx: ExecutionContext = None) -> sqlite3.Connection:
        """Retrieves a connection - do not forget to close() that once finished! If this instanbce is already closed then raising an error"""
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        if self.is_closed:
            err = "This DB is already closed"
            self._LOG.error(err, **labels)
            raise errors.ServiceRuntimeError(err, "already_closed")
        
        self._LOG.debug("connecting to db file: %s ...", self.config.db_file, **labels)
        conn = sqlite3.connect(database = self.config.db_file)
        conn.row_factory = sqlite3.Row
        self._LOG.debug("connection is created", **labels)

        return conn

    def is_available(self) -> bool:
        """Tells if the connection is still there, not closed yet"""
        return not self.is_closed


    def close(self, cntx: ExecutionContext = None) -> None:
        """Closing this DB permanently - no more connections possible after this"""
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()
        if self.is_closed:
            self._LOG.warning("already closed...", **labels)
            return
        
        self._LOG.info("closing...", **labels)

        # TODO would it make sense to force close all handed out connections? for now just leave it just do not add more

        self.is_closed = True

        self._LOG.info("now connection closed", **labels)