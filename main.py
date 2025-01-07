import sys
import os
import argparse
from src.observability.logging import LoggerFactory
from src.observability.common import buildGlobalLabels
from src.service.base_service import BaseService, AppType
from src.controller.customer_crud import CustomerCRUDController
from src.persistence.sqlite_customer_crud_dao import SqliteCustomerDAO
from src.config.models import ServiceConfig
from src.api.http.customer_handler_v1 import CustomerHandlerV1
from fastapi import FastAPI



ENVVAR_CFG_PATH = "BANKINGSERVICE_CFG_PATH"
ENVVAR_LOG_CFG_PATH = "BANKINGSERVICE_LOGCFG_PATH"
ARGUMENT_CFG_PATH = "--cfg"
ARGUMENT_LOG_CFG_PATH = "--logCfg"

class Service:
    async def process(self) -> str:
        return "OK"


class BankingService(BaseService):

    service_config: ServiceConfig

    customer_DAO: SqliteCustomerDAO
    customer_CRUD_controller: CustomerCRUDController


    def _buildDependencies(self) -> None:
        BankingService.customer_DAO = SqliteCustomerDAO(config = self.configDict)
        BankingService.customer_CRUD_controller = CustomerCRUDController(config=self.configDict, customer_DAO=BankingService.customer_DAO)

    def _loadConfig(self, configFilePath = None):
        super()._loadConfig(configFilePath)

        # let's transform the config Dict into our class based config model
        configObj = ServiceConfig(**self.configDict)
        BankingService.service_config = configObj
        

def _startService() -> None:

    # Let's parse the command line args
    parser = argparse.ArgumentParser(
                    description='A service which provides banking operations - see README.md (in Git repo) for more details'
                    )
    parser.add_argument(ARGUMENT_CFG_PATH, dest="cfg", default=None, required=False, help="path to the config .yaml file to use - you can also provide it via env variable " + ENVVAR_CFG_PATH)
    parser.add_argument(ARGUMENT_LOG_CFG_PATH, dest="logCfg", default=None, required=False, help="path to the logging config .yaml file to use - you can also provide it via env variable " + ENVVAR_LOG_CFG_PATH)
    args = vars(parser.parse_args())

    # Observability needs global labels - let's build it
    globalLabels = buildGlobalLabels()

    # Now as a very first step let's configure the logging - we need it badly
    logCfgFilePath = args["logCfg"]
    if logCfgFilePath == None:
        # fallback to env variable
        logCfgFilePath = os.environ.get(ENVVAR_LOG_CFG_PATH)
    if logCfgFilePath == None:
        print("WARNING! You did not provide log config file location... You could/should by using either "+ARGUMENT_LOG_CFG_PATH+" command line argument or "+ENVVAR_LOG_CFG_PATH+" environment variable! Therefore for now we use basic log config...", file=sys.stderr)
    LoggerFactory.configure_logging(logCfgFilePath=logCfgFilePath, globalLabels=globalLabels)

    # now obtain a logger and stat chitchatting from now
    LOG = LoggerFactory.get_logger('main')

    LOG.info("logging is now configured!")

    cfgFilePath = args["cfg"]
    if cfgFilePath == None:
        cfgFilePath = os.environ.get(ENVVAR_CFG_PATH)
    if cfgFilePath == None:
        # not good!
        LOG.error("Oops! You did not provide config file location... Service does not know how to configure itself. Please use either "+ARGUMENT_CFG_PATH+" command line argument or "+ENVVAR_CFG_PATH+" environment variable!")
        exit(1)
    LOG.info("config file to be used: %s", cfgFilePath)

    # Let's create the service instance
    service = BankingService(appType=AppType.FastAPI, configFilePath=cfgFilePath, logConfigFilePath=logCfgFilePath)
    
    # bind the FastAPI handlers
    app: FastAPI = service.get_FastAPI_app()
    customer_handler = CustomerHandlerV1(customer_crud_contoller=BankingService.customer_CRUD_controller, service_config=BankingService.service_config)
    customer_handler.attach_to_http_server(app)

    # finally, fire it up
    service.startServiceAndWaitForExit()

# We fire up the service if we are the Main!
if __name__ == "__main__":
    _startService()