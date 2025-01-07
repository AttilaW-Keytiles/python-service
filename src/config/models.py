from src.util import simple_dict_util

class FastAPIConfig:

    def __init__(self, **entries):
        if entries == None:
            return
        self.http_port: int = int(simple_dict_util.dict_getNumberByAny(theDict=entries, keys={"http_port", "httpPort"}, default=0))

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
        self.metrics_conf = FastAPIConfig(**simple_dict_util.dict_getDictByAny(theDict=entries, keys={"metrics"}, default=dict()))


