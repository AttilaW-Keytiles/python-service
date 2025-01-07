import logging
import json
import json_log_formatter
import re
from datetime import datetime, timezone

_DO_NOT_ADD_TO_EXTRA = json_log_formatter.BUILTIN_ATTRS.union({'extra'})

def _fixed_extra_from_record(record):
    """
    json_log_formatter.JSONFormatter has a bug in its method - it can add key 'extra' to the extras... recursively.
    this is a fixed version
    """
    return {
        attr_name: record.__dict__[attr_name]
        for attr_name in record.__dict__
        if attr_name not in _DO_NOT_ADD_TO_EXTRA
    }


class CustomisedPlainFormatter(logging.Formatter):
    """
    Extending the standard logging Formatter and fixing the problem it is actually loosing the 'extra' parameters one attached (dict) to log events.

    Fix is inspired by how json_log_formatter.JSONFormatter is doing this and kinda reusing that mechanism.
    """

    def __init__(self, fmt = None, datefmt = None, style = "%", validate = True, *, defaults = None):
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)


    def format(self, record):
        record.extra = _fixed_extra_from_record(record)
        s = super().format(record)
        return s

class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    """
    A standard Python logging formatter which adds some log event attribute manipulation possibilties to the base JSONFormatter class.

    Extra constructor named parameters (You can also add these to log config file under `formatters` entry and configure from there!):
     * `reorderAttributes`: Optional. If set this must be an array of attributes. When given then the formatter makes sure that attributes listed here will be the first entries
        in the attribute dictionary (which are not listed will just still pick up random order).
        This feature is useful in local development where 'human readability' might be important. For log collection it does not make much sense you just wasting resources... So do not set in PROD.
     * `attributesRemap`: this is a dict[str, any] map. The formatter will basically "re-map" the event attributes. During this you can drop stuff, add new/more.
       The Key is identifiying the attribute name in the event and the Value tells the formatter what to do with it. So it is basically an operation.
       Supported operations (Values) are the following:
        * `!drop`: the attribute will be removed from the event
        * `!record_get(<LogRecord attribute name>)`: the attribute will be added by reading the given LogRecord attribute. So this is enrichment basically.
          Supported LogRecord attributes: 
           * 'filename'
           * 'funcName'
           * 'levelname' - the log level
           * 'lineno'
           * 'module'
           * 'name' - the name of the logger
           * 'pathname
           * 'process'
           * 'processName'
           * 'stack_info'
           * 'thread'
           * 'threadName'
    """

    RECORD_GET_OP_MATCHER = '!record_get\((?P<attrName>[^\)]*)\)'

    def __init__(self, fmt = None, datefmt = None, style = "%", validate = True, *, defaults = None, attributesRemap: dict[str, any] = None, reorderAttributes: list[str] = None):
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        self._attributesRemap = attributesRemap
        if len(reorderAttributes) > 0:
            self._reorderAttributes = reorderAttributes
        else:
            self._reorderAttributes = None

    def extra_from_record(self, record):
        return _fixed_extra_from_record(record)

    def json_record(self, message, extra, record):

        # let our super create the dictionary
        event = super().json_record(message, extra, record)

        # let's fix the "time" attribute
        # it looks - for some reason - JSONFormatter instead of using record timestamp just using now() ... why??? but doesnt feel good
        # TODO - timezone... all printed times this way will be written in UTC (it looks) wich is OK for collection but not really human friendly and easy to make stupid mistake during investigation...
        event['time'] = datetime.fromtimestamp(record.created, tz=timezone.utc)

        # and now let's manipulate its entries!
        for key, value in self._attributesRemap.items():

            assignedValue = None
            removeAttrib = False
            if value.startswith("!"):
                if value == "!drop":
                    # we remove the attribute from the dictionary
                    removeAttrib = True
                else:
                    match = re.search(CustomisedJSONFormatter.RECORD_GET_OP_MATCHER, value)
                    if match != None:
                        # We need 
                        attrName = match.group('attrName')
                        attrName = attrName.replace('"', '')
                        if hasattr(record, attrName):
                            assignedValue = getattr(record, attrName)

            if removeAttrib:
                event.pop(key)
            if assignedValue != None:
                event[key] = assignedValue

        # finally, reorder the attributes if needed
        if self._reorderAttributes != None:
            reordered = dict()
            # iterate through the listed keys first
            for key in self._reorderAttributes:
                reordered.update({key: event.pop(key)})
            # let's add the rest
            reordered.update(event)
            event = reordered

        return event