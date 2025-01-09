from src.model.config.models import MetricsConfig
from src.observability.logging import Logger, LoggerFactory
from src.context.contexts import ExecutionContext
import prometheus_client

class MetricSet:
    pass

class HttpEndpointMetrics(MetricSet):
    """
    Useful for HTTP endpoints. This handy class brings a set of metrics optimized for HTTP typical scenarios.

    When you have a HTTP endpoint you simply go to the MetricsFactory.get_http_endpoint_metrics() method and get an instance of this class.
    Once you have the instance all you need to do is once you finished generating the response you invoke the .increment() method of it - passing over
    the http_status code you ended up with. This will dynamically create a Counter instance - if not yet exists - for that particular status_code and start counting.
    """

    _counter_template: prometheus_client.Counter = None

    @classmethod
    def _get_counter_template(cls) -> prometheus_client.Counter:
        # we do it only once
        if cls._counter_template == None:
            # These will act as a family
            label_names: set[str] = set(MetricsFactory.global_labels.keys())
            label_names.add('endpoint')
            label_names.add('status_code')
            label_names.add('method')
            cls._counter_template = prometheus_client.Counter('http_count', 'Count of events groupped by status code (200, 201, 400, ...) and method (POST, GET, ...)', labelnames=label_names)
        return cls._counter_template


    def __init__(self, endpoint_name: str):
        self.endpoint_name = endpoint_name
        self._counters: dict[str, any] = dict()

    def increment(self, status_code: str|int = 0, method: str = "?") -> None:
        """Once you finished the response generation and know your status_code simply invoke this to get an incremented Count for that status code"""
        key = f"{status_code}_{method}"
        counter_instance = self._counters.get(key)
        if counter_instance == None:
            counter_tpl = self._get_counter_template()
            counter_instance = counter_tpl.labels(endpoint = self.endpoint_name, status_code = status_code, method = method, **MetricsFactory.global_labels)
            self._counters.update({key: counter_instance})
        counter_instance.inc()



class MetricsFactory:
    """Static class helping you to deal with metrics"""

    @classmethod
    def configure_metrics(cls, config: MetricsConfig, global_labels: dict[str, any] = None):
        cls._LOG: Logger = LoggerFactory.getLogger("service.observability.MetricsFactory")

        cls.config: MetricsConfig = config
        cls.global_labels: dict[str, any] = global_labels

        cls._metric_sets: dict[str, MetricSet] = dict()

        if not cls.config.GC_COLLECTOR_enabled:
            prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
        if not cls.config.PLATFORM_COLLECTOR_enabled:
            prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
        if not cls.config.PROCESS_COLLECTOR_enabled:
            prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

    @classmethod
    def start_prometheus_scraping_endpoint(cls, cntx: ExecutionContext = None) -> None:
        """Starts the Prometheus metrics endpoint - unless disabled by config..."""
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()

        if not cls.config.is_enabled:
            cls._LOG.info("metrics is disabled by config - skipping starting Prometheus endpoint", **labels)
            return

        prometheus_client.start_http_server(port = cls.config.http_port)
        cls._LOG.info("Prometheus metrics endpoint is running on http://localhost:%s", cls.config.http_port, **labels)

    @classmethod
    def get_http_endpoint_metrics(cls, endpoint_name: str, cntx: ExecutionContext = None) -> HttpEndpointMetrics:
        labels = cntx.get_minimmal_info_for_log() if cntx != None else dict()

        metric_set = cls._metric_sets.get("http:"+endpoint_name)
        if metric_set == None:
            metric_set  = HttpEndpointMetrics(endpoint_name=endpoint_name)
            # let's save it
            cls._metric_sets.update({"http:"+endpoint_name: metric_set})
            cls._LOG.info("created HttpEndpointMetrics with endpoint name '%s'", endpoint_name, **labels)
        return metric_set


