from fastapi import Request
from src.util import preconditions, ids
from src.model.auth.auth_info import AuthInfo
import time

class ExecutionContext(object):
    """
    This context can carry information through backend function call-chain - letting each participants know the invocation context.

    Normally this context is created at the first public endpoint within the system someone invokes - no matter if this is a HTTP / gRPC endpoint or Event consuming from a Message Broker.
    Carries crucial information to uniquely identify a given business transaction.

    To ensure good observability you should make sure you decorate your log event with at least the `transactionId` and the `traceId` as labels!
    The context help ypu doing that - see methods!
    """
    
    def __init__(self, transaction_id: str = None, trace_id: str = None, auth_info: AuthInfo = None, **kwargs):
        # we keep the timestamp of our creation - UTC Epoch
        self.created_ts = time.time()
        """When was this context created? Linux UTC timestamp (since Epoch)"""

        self.transaction_id = transaction_id
        """The transactionId associated with this context"""
        if self.transaction_id == None:
            self.transaction_id = ids.generate_uuid()

        self.trace_id = trace_id
        """The traceId associated with this context"""
        if self.trace_id == None:
            self.trace_id = ids.generate_uuid()

        self.auth_info = auth_info
        """Who is authenticated on this context? can be nobody..."""

        if kwargs != None:
            for key, value in kwargs:
                setattr(self, key, value)

    def get_minimmal_info_for_log(self) -> dict[str, any]:
        """
        Use this function to fetch minimalistic info you should decorate your log events with to correlate things nicely!
        """
        data = {
            'transId': self.transaction_id,
            'traceId': self.trace_id
        }
        # if we have loggen in user let's add his ID - this way we can also search logs based on UserID later (not bad for audit...)
        if self.auth_info != None:
            data.update({"userId": self.auth_info.user_id})
        return data

    
    def get_ellapsed_millis(self, toTs: float = 0) -> int:
        """
        To easily query how many milliseconds has ellapsed since this context was created.
        """
        if toTs == 0:
            toTs = time.time()
        millis = toTs - self.created_ts
        millis *= 1000
        return int(millis)
    
    def get_http_response_headers(self) -> dict[str, str]:
        """
        Returns a dictionary which you should set on your HTTP Response headers - info coming from this context.
        """
        headers: dict[str, str] = dict()
        if self.trace_id != None:
            # we put in both forms - unfortunately not really standard among systems...
            headers['x-trace-id'] = self.trace_id
            headers['trace-id'] = self.trace_id
        if self.transaction_id != None:
            headers['x-transaction-id'] = self.transaction_id

        return headers    


class FastAPIHttpExecutionContext(ExecutionContext):

    def __init__(self, http_request: Request, transaction_id = None, trace_id = None, auth_info = None, **kwargs):
        self.http_request = http_request
        preconditions.check_argument(http_request != None and isinstance(http_request, Request), "'http_request' can not be None and must be a fastapi.Request")

        headers = http_request.headers
        traceIdHeader = headers.get('x-trace-id')
        if traceIdHeader == None:
            traceIdHeader = headers.get('x-traceid')
        if traceIdHeader == None:
            traceIdHeader = headers.get('trace-id')
        if traceIdHeader != None:
            # override the traceId - no matter what was possibly given
            trace_id = traceIdHeader

        super().__init__(transaction_id, trace_id, auth_info)
