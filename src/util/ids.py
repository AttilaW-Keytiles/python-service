import uuid
import string
import random

def generate_uuid() -> str:
    """
    We use this method everywhere in our code to generate a UUID - for now we use UUID v4
    """
    return str(uuid.uuid4())

def generate_random_word(length: int = 16, valid_characters: str = None) -> str:
    """
    Generates a random string of the specified length.
    The string contains uppercase, lowercase letters, and numbers.

    :param length: The length of the generated string. Default is 10.
    :return: A random string.
    """
    if valid_characters == None:
        valid_characters = string.ascii_letters + string.digits  # Uppercase, lowercase letters, and digits

    return ''.join(random.choice(valid_characters) for _ in range(length))
