import uuid

def generate_uuid() -> str:
    """
    We use this method everywhere in our code to generate a UUID - for now we use UUID v4
    """
    return str(uuid.uuid4())