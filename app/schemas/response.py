from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    message: str
    details: Optional[object] = None


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T]
    error: Optional[ApiError]
    is_error: bool


def success_response(data: Optional[T] = None) -> dict:
    return {
        "data": data,
        "error": None,
        "is_error": False,
    }


def error_response(message: str, details: Optional[object] = None) -> dict:
    return {
        "data": None,
        "error": {
            "message": message,
            "details": details,
        },
        "is_error": True,
    }
