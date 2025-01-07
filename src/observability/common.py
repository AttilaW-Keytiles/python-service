import os


def buildGlobalLabels() -> dict[str, any]:
    """
    Build a dictionary whos key-value pairs will serve as labels in logging and monitoring.

    This is done by scanning environment variables (due to our never agreed standards but not bad practice... :-P)
    """

    serviceName = os.environ.get("SERVICE_NAME")
    if serviceName == None:
        serviceName = os.environ.get("CONTAINER_NAME")
    if serviceName == None:
        serviceName = "?"

    serviceVer = os.environ.get("SERVICE_VERSION")
    if serviceVer == None:
        serviceVer = os.environ.get("CONTAINER_VERSION")
    if serviceVer == None:
        serviceVer = "?"

    host = os.environ.get("HOSTNAME")
    if host == None:
        host = os.environ.get("HOST")
    if host == None:
        host = "?"

    instanceId = os.environ.get("INSTANCE_ID")
    if instanceId == None:
        instanceId = "?"

    return {
        "serviceName": serviceName,
        "serviceVer": serviceVer,
        "host": host,
        "instId": instanceId
    }