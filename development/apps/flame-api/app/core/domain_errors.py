"""Stable domain error codes; HTTP representation remains compatible."""
from fastapi import HTTPException


def fail(status: int, code: str):
    raise HTTPException(status, code)
