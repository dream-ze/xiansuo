from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str = "ok"


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = 0
    page: int = 1
    page_size: int = 20


def success_response(data: Any | None = None, message: str = "ok") -> dict[str, Any]:
    return {
        "success": True,
        "data": {} if data is None else data,
        "message": message,
    }


def error_response(message: str = "error message") -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "message": message,
    }
