from src.util import simple_dict_util

class FastAPIConfig:

    def __init__(self, **entries):
        if entries == None:
            return
        self.http_port: int = int(simple_dict_util.dict_getNumberByAny(theDict=entries, keys={"http_port", "httpPort"}, default=0))

class SqliteConfig:

    def __init__(self, **entries):
        if entries == None:
            return
        self.db_file: str = simple_dict_util.dict_getStringByAny(theDict=entries, keys={"db_file", "dbFile"})
        self.schema_files: dict[str, list[str]] = simple_dict_util.dict_getDictByAny(theDict=entries, keys={"schema_files", "schemaFiles"})
        """Each key can contain multiple files - different DAOs using different keys"""

class PersistenceConfig:

    def __init__(self, **entries):
        if entries == None:
            return
        self.sqlite_config = SqliteConfig(**simple_dict_util.dict_getDictByAny(theDict=entries, keys={"sqlite"}, default=dict()))


class MetricsConfig:

    def __init__(self, **entries):
        if entries == None:
            return
        self.is_enabled: bool = simple_dict_util.dict_getBoolByAny(theDict=entries, keys={"is_enabled", "isEnabled"})
        self.http_port: int = int(simple_dict_util.dict_getNumberByAny(theDict=entries, keys={"http_port", "httpPort"}, default=0))


class ServiceConfig:
    
    def __init__(self, **entries):
        if entries == None:
            return
        self.fast_api_conf = FastAPIConfig(**simple_dict_util.dict_getDictByAny(theDict=entries, keys={"fast_api", "fastAPI", "fastApi"}, default=dict()))
        self.persistence_config = PersistenceConfig(**simple_dict_util.dict_getDictByAny(theDict=entries, keys={"persistence"}, default=dict()))
        self.metrics_conf = FastAPIConfig(**simple_dict_util.dict_getDictByAny(theDict=entries, keys={"metrics"}, default=dict()))


