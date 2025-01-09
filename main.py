import sys
import os
import argparse
from src.observability.logging import LoggerFactory, Logger
from src.observability.common import buildGlobalLabels
from src.service.base_service import BaseService, AppType
from src.controller.customer_crud import CustomerCRUDController
from src.controller.account_crud import AccountCRUDController
from src.controller.account_operations import AccountOperationsController
from src.controller.transfer_crud import TransferCRUDController
from persistence.sqlite.sqlite_customer_dao import SqliteCustomerDAO
from persistence.sqlite.sqlite_account_dao import SqliteAccountDAO
from persistence.sqlite.sqlite_transfer_dao import SqliteTransferDAO
from persistence.sqlite.sqlite_user_dao import SqliteUserDAO
from src.persistence.sqlite.sqlite_db import SqliteDB
from src.model.config.models import ServiceConfig
from src.api.http.customer_handler_set_v1 import CustomerHandlerSetV1
from src.api.http.account_handler_set_v1 import AccountHandlerSetV1
from src.api.http.transfer_handler_set_v1 import TransferHandlerSetV1
from src.api.http.authenticator import HttpAuthenticator
from src.model.error import errors
from fastapi import FastAPI


ENVVAR_CFG_PATH = "BANKINGSERVICE_CFG_PATH"
ENVVAR_LOG_CFG_PATH = "BANKINGSERVICE_LOGCFG_PATH"
ENVVAR_EXECUTION_PROFILE = "BANKINGSERVICE_PROFILE"
ARGUMENT_CFG_PATH = "--cfg"
ARGUMENT_LOG_CFG_PATH = "--logCfg"
ARGUMENT_EXECUTION_PROFILE = "--profile"

class Service:
    async def process(self) -> str:
        return "OK"


class BankingService(BaseService):

    _LOG: Logger = LoggerFactory.getLogger("service.BankingService")

    service_config: ServiceConfig
    """Our parsed config"""
    customer_CRUD_controller: CustomerCRUDController
    """Reference to the customer CRUD based controller"""
    account_CRUD_controller: AccountCRUDController
    """Reference to the account CRUD based controller"""
    account_operations_controller: AccountOperationsController
    """Reference to the account ops based controller"""
    transfer_CRUD_controller: TransferCRUDController
    """Reference to the transfer CRUD based controller"""
    http_authenticator: HttpAuthenticator
    """Reference to the Authenticator we can use in HTTP handlers"""

    sqlite_db: SqliteDB
    """We keep this as it must be closed properly during shutdown"""


    def __init__(self, app_type = None, execution_profile = None, config_file_path = None, log_config_file_path = None):
        # this way the BaseService will also use our logger (at least in istance methods) - better loeg readability...
        self._LOG = BankingService._LOG
        super().__init__(app_type, execution_profile, config_file_path, log_config_file_path)


    def _build_dependencies(self, execution_profile: str = None) -> None:

        self._LOG.info("building dependencies for execution profile '%s' ...", execution_profile)

        match execution_profile:
            case None | "prod":

                # persistence layer
                BankingService.sqlite_db: SqliteDB = SqliteDB(config = BankingService.service_config.persistence_config.sqlite_config)
                customer_DAO = SqliteCustomerDAO(config = BankingService.service_config.persistence_config.sqlite_config, db = BankingService.sqlite_db)
                accounts_DAO = SqliteAccountDAO(config = BankingService.service_config.persistence_config.sqlite_config, db = BankingService.sqlite_db)
                transfers_DAO = SqliteTransferDAO(config = BankingService.service_config.persistence_config.sqlite_config, db = BankingService.sqlite_db)
                users_DAO = SqliteUserDAO(config = BankingService.service_config.persistence_config.sqlite_config, db = BankingService.sqlite_db)

                # controller layer
                BankingService.customer_CRUD_controller = CustomerCRUDController(config=BankingService.service_config, customer_DAO=customer_DAO)
                BankingService.account_CRUD_controller = AccountCRUDController(config=BankingService.service_config, account_DAO=accounts_DAO, customer_DAO=customer_DAO)
                BankingService.account_operations_controller = AccountOperationsController(config=BankingService.service_config, account_ops_DAO=accounts_DAO, account_crud_DAO=accounts_DAO, customer_crud_DAO=customer_DAO)
                BankingService.transfer_CRUD_controller = TransferCRUDController(config=BankingService.service_config, account_DAO=accounts_DAO, transfer_DAO=transfers_DAO)

                # other
                BankingService.http_authenticator = HttpAuthenticator(config = BankingService.service_config, user_provider = users_DAO)

            case _:
                err = f"Unkown profile '{execution_profile}'! Can not build dependencies for this setup..."
                BankingService._LOG.error(err)
                raise errors.ServiceRuntimeError("unknown_execution_profile", err)

        self._LOG.debug("dependencies built and wired successfuly")


    def _load_config(self, configFilePath = None):
        super()._load_config(configFilePath)

        # let's transform the config Dict into our class based config model
        configObj = ServiceConfig(**self.config_dict)
        BankingService.service_config = configObj
        

def _startService() -> None:

    # Let's parse the command line args
    parser = argparse.ArgumentParser(
                    description='A service which provides banking operations - see README.md (in Git repo) for more details'
                    )
    parser.add_argument(ARGUMENT_CFG_PATH, dest="cfg", default=None, required=False, help="path to the config .yaml file to use - you can also provide it via env variable " + ENVVAR_CFG_PATH)
    parser.add_argument(ARGUMENT_LOG_CFG_PATH, dest="logCfg", default=None, required=False, help="path to the logging config .yaml file to use - you can also provide it via env variable " + ENVVAR_LOG_CFG_PATH)
    parser.add_argument(ARGUMENT_EXECUTION_PROFILE, dest="executionProfile", default=None, required=False, help="in which execution profile you want to launch the service - you can also provide it via env variable " + ENVVAR_EXECUTION_PROFILE)
    args = vars(parser.parse_args())

    # Observability needs global labels - let's build it
    global_labels = buildGlobalLabels()

    # Now as a very first step let's configure the logging - we need it badly
    log_cfg_file_path = args["logCfg"]
    if log_cfg_file_path == None:
        # fallback to env variable
        log_cfg_file_path = os.environ.get(ENVVAR_LOG_CFG_PATH)
    if log_cfg_file_path == None:
        print("WARNING! You did not provide log config file location... You could/should by using either "+ARGUMENT_LOG_CFG_PATH+" command line argument or "+ENVVAR_LOG_CFG_PATH+" environment variable! Therefore for now we use basic log config...", file=sys.stderr)
    LoggerFactory.configure_logging(logCfgFilePath=log_cfg_file_path, globalLabels=global_labels)

    # now obtain a logger and stat chitchatting from now
    LOG:Logger = LoggerFactory.get_logger('main')

    LOG.info("logging is now configured!")

    cfg_file_path = args["cfg"]
    if cfg_file_path == None:
        cfg_file_path = os.environ.get(ENVVAR_CFG_PATH)
    if cfg_file_path == None:
        # not good!
        LOG.error("Oops! You did not provide config file location... Service does not know how to configure itself. Please use either "+ARGUMENT_CFG_PATH+" command line argument or "+ENVVAR_CFG_PATH+" environment variable!")
        exit(1)
    LOG.info("config file to be used: %s", cfg_file_path)

    execution_profile = args["executionProfile"]
    if execution_profile == None:
        execution_profile = os.environ.get(ENVVAR_EXECUTION_PROFILE)
    LOG.info("execution profile of the service is: %s", execution_profile)

    # Let's create the service instance
    service = BankingService(app_type = AppType.FastAPI, config_file_path = cfg_file_path, log_config_file_path = log_cfg_file_path)
    
    # instantiate and bind the FastAPI handlers
    app: FastAPI = service.get_FastAPI_app()
    customer_handlers = CustomerHandlerSetV1(
        # dependency injection
        service_config=BankingService.service_config,
        customer_crud_contoller=BankingService.customer_CRUD_controller,
        authenticator = BankingService.http_authenticator
    )
    customer_handlers.attach_to_http_server(app)
    account_handlers = AccountHandlerSetV1(
        # dependency injection
        service_config=BankingService.service_config,
        account_crud_contoller=BankingService.account_CRUD_controller,
        account_operation_controller=BankingService.account_operations_controller,
        authenticator = BankingService.http_authenticator
    )
    account_handlers.attach_to_http_server(app)
    transfer_handlers = TransferHandlerSetV1(
        # dependency injection
        service_config=BankingService.service_config,
        transfer_crud_contoller=BankingService.transfer_CRUD_controller,
        authenticator = BankingService.http_authenticator
    )
    transfer_handlers.attach_to_http_server(app)

    # finally, fire it up
    service.start_service_and_wait_for_exit()

    LOG.info("shutting down...")
    if BankingService.sqlite_db != None:
        BankingService.sqlite_db.close()

# We fire up the service if we are the Main!
if __name__ == "__main__":
    _startService()