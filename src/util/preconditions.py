
def check_argument(condition_fulfill: bool, err_msg_template: str, *args):
    if not condition_fulfill:
        if str != None and not isinstance(err_msg_template, str):
            err_msg_template = str(err_msg_template)
        err = err_msg_template.format(*args)
        raise ValueError(err)