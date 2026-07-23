from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    error: bool = False
    message: str = "OK"
    payload: Optional[T] = None


class ProgressPayload(BaseModel):
    status: str
    total_files: int
    downloaded_files: int
    current_message: str


class FileItemPayload(BaseModel):
    id: int
    name: str
    downloaded_at: Optional[datetime]
    has_content: bool


class FilesListPayload(BaseModel):
    total: int
    page: int
    page_size: int
    files: list[FileItemPayload]


class FileStatItemPayload(BaseModel):
    file_id: int
    file_name: str
    counts: dict[str, int]


class CalculateStatsPayload(BaseModel):
    total_statistics: dict[str, int]
    file_statistics: list[FileStatItemPayload]


class CalculateRequest(BaseModel):
    file_ids: list[int]
