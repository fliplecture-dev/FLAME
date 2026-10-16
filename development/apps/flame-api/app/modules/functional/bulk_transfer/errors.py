from fastapi import HTTPException


class BulkFailure(HTTPException):
    """Only explicitly authored bulk-operation messages may pass through to the UI."""


def fail(status, message):
    raise BulkFailure(status, message)
