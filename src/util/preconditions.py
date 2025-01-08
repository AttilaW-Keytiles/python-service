from enum import Enum

def check_argument(condition_fulfill: bool, err_msg_template: str, *args, **kwargs):
    if not condition_fulfill:
        if str != None and not isinstance(err_msg_template, str):
            err_msg_template = str(err_msg_template)
        err = err_msg_template.format(*args, **kwargs)
        raise ValueError(err)
    
def is_enum_value_valid(the_value_to_test: any, the_enum_type: Enum) -> bool:
    if any == None:
        return True
    if isinstance(the_value_to_test, the_enum_type):
        return True
    if isinstance(the_value_to_test, str):
        return the_value_to_test in {status.value for status in the_enum_type}
    return False

def check_enum_value(the_value_to_test: any, the_enum_type: Enum, err_msg_template: str, *args, **kwargs):
    if not is_enum_value_valid(the_value_to_test, the_enum_type):
        if str != None and not isinstance(err_msg_template, str):
            err_msg_template = str(err_msg_template)
        err = err_msg_template.format(*args, **kwargs)
        raise ValueError(err)
