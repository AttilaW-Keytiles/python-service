from src.observability.logging import Logger

def check_argument(condition_fulfill: bool, err_msg_template: str = "", logger: Logger = None, **msg_resolve_vars):
    if not condition_fulfill:
        err = err_msg_template.format(kwargs=msg_resolve_vars)
        if logger != None:
            logger.error(err)
        raise ValueError(err)