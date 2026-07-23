from typing import Optional, Any
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.api_v1_service import FileService
from src.dependencies import get_target_api, get_db
from src.services.api_v1_service import FileService
from src.services.target_api import TargetAPI
from src.schemas import BaseResponse

router = APIRouter()


@router.post("/download/start", response_model=BaseResponse)
async def start_download(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    target_api: TargetAPI = Depends(get_target_api),
):
    try:
        service = FileService(db, target_api)
        background_tasks.add_task(service.start_download)
        return BaseResponse(message="Скачивание запущено в фоновом режиме")
    except Exception as e:
        return BaseResponse(error=True, message="Не удалось запустить скачивание")


@router.get("/download/progress", response_model=BaseResponse)
async def get_download_progress():
    try:
        payload = FileService.get_progress()
        return BaseResponse(payload=payload)
    except Exception as e:
        return BaseResponse(error=True, message="Не удалось получить прогресс")


@router.get("/files", response_model=BaseResponse)
async def get_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    ids_only: bool = False,
    sort_by: str = Query("downloaded_at", pattern="^(downloaded_at|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    target_api: TargetAPI = Depends(get_target_api),
):
    try:
        service = FileService(db, target_api)

        if ids_only:
            payload = await service.get_all_file_ids()
            return BaseResponse(payload={"file_ids": payload})
        else:
            payload = await service.get_files(
                page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
            )
            return BaseResponse(payload=payload)
    except Exception as e:
        return BaseResponse(error=True, message="Не удалось получить список файлов")


@router.post("/calculate", response_model=BaseResponse)
async def calculate_statistics(
    request: dict,
    db: AsyncSession = Depends(get_db),
    target_api: TargetAPI = Depends(get_target_api),
):
    try:
        service = FileService(db, target_api)
        file_ids = request.get("file_ids", [])
        payload = await service.calculate_statistics(file_ids)
        return BaseResponse(payload=payload)
    except Exception as e:
        return BaseResponse(error=True, message="Не удалось рассчитать статистику")
