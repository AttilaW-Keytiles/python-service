#from structlog import getLogger as StructlogGetLogger, configure
#from structlog.stdlib import LoggerFactory as StructlogLoggerFactory
#from structlog.processors import KeyValueRenderer, JSONRenderer, EventRenamer
import structlog
import logging.config
import yaml

"""
**Note:** The 'observability' package could be externalized into a library and become a shared code. If we would have already agreed standards...
          But as we do not have them clearly, for now it stays here
"""

class Logger:
    """
    A Class which is wrapping the underlying logging framework - service code is using this.
    This way we can change underlying logging easily.
    """

    def __init__(self, name: str):
        # let's get the wrapped underlying logger
        self._logger: structlog.BoundLogger = structlog.getLogger(name, LoggerFactory._globalLabels)

    def error(self, *args, **namedArgs):
        self._logger.error(*args, **namedArgs)

    def warning(self, *args, **namedArgs):
        self._logger.warning(*args, **namedArgs)

    def info(self, *args, **namedArgs):
        self._logger.info(*args, **namedArgs)

    def debug(self, *args, **namedArgs):
        self._logger.debug(*args, **namedArgs)


def enrich_with_globallabels(_, __, ed):
    # lets merge in all global labels
    ed.update(LoggerFactory._globalLabels)
    return ed

class LoggerFactory:
    """
    A Factory class to create Logger instances. This class has static methods to allow service code can easily interact with it from anywhere.
    """

    # static private dictionary of created logger instances
    _loggers: dict[str, Logger] = dict()

    # let's start empty
    _globalLabels: dict[str, any] = dict()

    @staticmethod
    def configure_logging(logCfgFilePath: str|None, globalLabels: dict[str, any]) -> None:
        
        LoggerFactory._globalLabels = globalLabels

        if logCfgFilePath == None:
            print("LoggerFactory: configuring logging - since no config file provided using defaults")
            logging.basicConfig()
        else:
            print("LoggerFactory: configuring logging - log config file to be used: " + logCfgFilePath)
            # Load the config file
            with open(logCfgFilePath, 'rt') as f:
                config = yaml.safe_load(f.read())
            # Configure the logging module with the config file
            logging.config.dictConfig(config)

        structlog.configure(logger_factory=structlog.stdlib.LoggerFactory(), processors=[
            enrich_with_globallabels,
            structlog.stdlib.render_to_log_kwargs
        ])

    # class method to get a logger
    @staticmethod
    def get_logger(name: str) -> Logger:
        logger = LoggerFactory._loggers.get(name)
        if logger == None:
            logger = Logger(name)
            LoggerFactory._loggers.update({name: logger})
        return logger
    
    getLogger = get_logger  # noqa: N816
    """
    CamelCase alias for `get_logger`.
    """    