import uvicorn
import fastapi
from src.observability.logging import LoggerFactory, Logger
from enum import Enum
import yaml
from src.util import simple_dict_util
from src.config.models import FastAPIConfig

# more can follow if we need... comes with more work too... :-P
class AppType(Enum):
    FastAPI = 1


class BaseService:
    """
    Abstract Class to abstracting away the concrete underlying App framework / implementation.
    To use this you need to extnd this class in your business logic and implement the abstract methods.
    
    You can have only one Service at a time so follows (sort of) Singleton pattern. If you try to instantiate a subclass more than once you get an error.

    AttilaW Note: no point to over do this now! I'm more like just experimenting with it for now to feel the approach and have a clean placeholder for boilerplate code bootstraps everything.
    """

    _LOG: Logger = LoggerFactory.getLogger("service.BaseService")

    # Our Singleton instance
    _instance: any = None

    @staticmethod
    def get_instance() -> any:
        return BaseService._instance

    @staticmethod
    def _must_get_instance() -> any:
        if BaseService._instance == None:
            err = "Operation failed! No service instance yet. First you need to extend BaseService class and create an instance!"
            BaseService._LOG.error(err)
            raise RuntimeError(err)
        return BaseService._instance

    # From where the config is loaded
    configFilePath: str
    # The parsed config - in Dict form
    configDict: dict[str, any] = None

    def get_FastAPI_app() -> fastapi.FastAPI:
        """
        Returns the singleton service instance underlying FastAPI app - if the service is that appType and you already have service instance. Fails otherwise.
        """
        instance = BaseService._must_get_instance()
        return instance.get_FastAPI_app()


    # Ideas taken from https://www.geeksforgeeks.org/singleton-pattern-in-python-a-complete-guide/ but decided with this - this way it can be overriden still works
    def __init__(self, appType: AppType = None, configFilePath: str = None, logConfigFilePath: str = None):
        """
        Creates a service instance of the given `appType`.

        Parameters:
         * `appType` - one of the supported Application types
         * `configFilePath` - which will be parsed and stored as config of this app.
        """

        self._LOG = BaseService._LOG

        self._LOG.debug("Instantiating service of appType '%s'...", appType)

        self._logConfigFilePath = logConfigFilePath

        # do we have an instance now already?
        if BaseService._instance != None:
            # let's make it simple now...
            err = "Failed to create service instance - you have already created one and you can just create one!"
            self._LOG.error(err)
            raise RuntimeError(err)
        # let's store this instance
        BaseService._instance = self
        self._LOG.debug("instance registered")

        # let's load the config from the file
        self._loadConfig(configFilePath=configFilePath)

        # let's create the underlying application
        self._LOG.debug("creating underlying App...")
        self._appType = appType
        self._app = None
        match appType:
            case AppType.FastAPI:
                self._createFastAPIApp()
            case _:
                err = f"Failed to create instance - unknown application type: {appType}"
                self._LOG.error(err)
                raise RuntimeError(err)
        self._LOG.debug("underlying App created")
        

        # give the chance to the subclass now to build it's dependencies!
        self._buildDependencies()
            
    def _buildDependencies(self) -> None:
        """
        Abstract method you need to implement in your subclass. This is invoked during constructor mechanism after config is loaded. And now you have your chance
        to create / store / wire together all your business objects your Service will use.
        """
        ...

    # Private helper. The type is FastAPI so this method is creating a FastAPI app
    def _createFastAPIApp(self) -> None:
        self._app = fastapi.FastAPI()

    # Private helper. Loading the config file and storing it's Dict form in the service
    def _loadConfig(self, configFilePath: str = None) -> None:
        self._LOG.debug("loading config from '%s' ...", configFilePath)

        if configFilePath == None:
            self.configDict = dict()
        else:
            # for now we take only .yaml file
            if configFilePath.lower().endswith(".yaml") or configFilePath.lower().endswith(".yml"):
                with open(configFilePath) as f:
                    try:
                        self.configDict = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        err = f"Failed to load config from '{configFilePath}' due to error: {e}"
                        self._LOG.error(err)
                        raise RuntimeError(err) from e
            else:
                err = f"Can not load config from '{configFilePath}' - for now only .yaml is supported"
                self._LOG.error(err)
                raise RuntimeError(err) from e
            
        self._LOG.debug("config is loaded into Dict form now")


    def startServiceAndWaitForExit(self):
        """
        Starts the service in a blocking fashion. This means service will wait for Term signal.
        """
        self._LOG.debug("starting service in blocking mode... will wait for Term signal")

        if self._appType == AppType.FastAPI:
            # let's see if we have "fast_api" section in our config! if yes convert it into our config model
            fast_api_conf = FastAPIConfig(**simple_dict_util.dict_getDictByAny(theDict=self.configDict, keys={"fast_api", "fastAPI", "fastApi"}, default=dict()))
            conf = {
                'host': 'localhost'
            }
            if fast_api_conf.http_port > 0:
                conf['port'] = fast_api_conf.http_port
            if self._logConfigFilePath != None:
                conf['log_config'] = self._logConfigFilePath

            uvicorn.run(self._app, **conf)

    # TODO Implement or remove! Come back to it later once we figured out how we want to do this!
    def stopService(self):
        """
        Stops the running service.
        """
        err = "stopService() method is not implemented yet, sorry :-("
        self._LOG.error(err)
        raise NotImplementedError(err)

    def get_FastAPI_app(self) -> fastapi.FastAPI:
        """
        Returning the service underlying FastAPI app - if the service is that appType. Fails otherwise.
        """
        if self._appType != AppType.FastAPI:
            err = f"Oops! Can not provide you FastAPI app - it looks your service appType is not FastAPI but {self._appType}"
            self._LOG.error(err)
            raise RuntimeError(err)
        return self._app


    def __str__(self):
        return f"BaseService[appType={self._appType}]"
