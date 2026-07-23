import logging
from io import BytesIO
from zipfile import ZipFile
from collections import Counter
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import File
from src.services.target_api import TargetAPI
from src.schemas import (
    ProgressPayload,
    FilesListPayload,
    FileItemPayload,
    CalculateStatsPayload,
    FileStatItemPayload,
)

logger = logging.getLogger(__name__)

download_progress = {
    "status": "idle",
    "total_files": 0,
    "downloaded_files": 0,
    "current_message": "Ожидание запуска...",
    "start_time": None,
}


class FileService:
    def __init__(self, db: AsyncSession, target_api: TargetAPI):
        self.db = db
        self.target_api = target_api

    async def start_download(self):
        global download_progress

        result = await self.db.execute(select(func.count(File.id)))
        total_files = result.scalar()
        result = await self.db.execute(
            select(func.count(File.id)).where(File.content.is_not(None))
        )
        downloaded_files = result.scalar()

        if total_files > 0 and total_files == downloaded_files:
            download_progress["status"] = "completed"
            download_progress["current_message"] = "✅ Все файлы уже скачаны!"
            logger.info("Все файлы уже скачаны, повторный запуск не требуется")
            return

        if download_progress["status"] in ["discovering", "downloading"]:
            logger.info("Процесс уже запущен")
            return

        download_progress["status"] = "discovering"
        download_progress["start_time"] = datetime.now().isoformat()
        download_progress["current_message"] = "Собираю имена файлов..."
        download_progress["total_files"] = 0
        download_progress["downloaded_files"] = 0

        try:
            await self._discovery_phase()

            download_progress["status"] = "downloading"
            download_progress["current_message"] = "Скачиваю контент..."
            await self._download_phase()

            download_progress["status"] = "completed"
            download_progress["current_message"] = "✅ Все файлы скачаны!"
            logger.info("Скачивание завершено успешно")

        except Exception as e:
            logger.error(f"Ошибка при скачивании: {e}", exc_info=True)
            download_progress["status"] = "error"
            download_progress["current_message"] = "Произошла ошибка при скачивании"
        finally:
            await self.target_api.close()

    async def _discovery_phase(self):
        global download_progress
        while True:
            names = await self.target_api.get_names()
            if not names:
                break

            files = [File(name=name) for name in names]
            self.db.add_all(files)
            await self.db.commit()

            await self.target_api.mark_downloaded(names)
            download_progress["total_files"] += len(names)
            logger.info(f"Собрано имён: {download_progress['total_files']}")

    async def _download_phase(self):
        global download_progress
        result = await self.db.execute(select(File).where(File.content.is_(None)))
        files_to_download = result.scalars().all()

        if not files_to_download:
            return

        names_list = [f.name for f in files_to_download]

        for i in range(0, len(names_list), 3):
            batch_names = names_list[i : i + 3]
            zip_bytes_list = await self.target_api.download(batch_names)

            for zip_bytes in zip_bytes_list:
                with ZipFile(BytesIO(zip_bytes)) as zf:
                    for file_info in zf.filelist:
                        content = zf.read(file_info.filename).decode("utf-8")
                        result = await self.db.execute(
                            select(File).where(File.name == file_info.filename)
                        )
                        file = result.scalar_one_or_none()

                        if file:
                            file.content = content
                            download_progress["downloaded_files"] += 1

            await self.db.commit()
            logger.info(
                f"Скачано {download_progress['downloaded_files']} из {download_progress['total_files']}"
            )

    def _count_digits(self, content: str) -> dict[str, int]:
        counts = {str(d): 0 for d in range(10)}
        char_counts = Counter(char for char in content if char.isdigit())
        for digit in counts.keys():
            counts[digit] = char_counts.get(digit, 0)
        return counts

    @staticmethod
    def get_progress() -> ProgressPayload:
        return ProgressPayload(
            **{k: v for k, v in download_progress.items() if k != "start_time"}
        )

    @staticmethod
    def get_start_time() -> Optional[str]:
        return download_progress.get("start_time")

    async def get_files(
        self,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "downloaded_at",
        sort_order: str = "desc",
    ) -> FilesListPayload:
        total_result = await self.db.execute(select(func.count(File.id)))
        total = total_result.scalar()

        offset = (page - 1) * page_size

        if sort_by == "status":
            order_column = File.content.is_not(None)
        else:
            order_column = File.downloaded_at

        if sort_order == "desc":
            primary_order = desc(order_column)
            secondary_order = desc(File.id)
        else:
            primary_order = asc(order_column)
            secondary_order = asc(File.id)

        result = await self.db.execute(
            select(File)
            .order_by(primary_order, secondary_order)
            .offset(offset)
            .limit(page_size)
        )
        files = result.scalars().all()

        file_items = [
            FileItemPayload(
                id=f.id,
                name=f.name,
                downloaded_at=f.downloaded_at,
                has_content=f.content is not None,
            )
            for f in files
        ]

        return FilesListPayload(
            total=total, page=page, page_size=page_size, files=file_items
        )

    async def get_all_file_ids(self) -> list[int]:
        result = await self.db.execute(select(File.id))
        return [row[0] for row in result.all()]

    async def calculate_statistics(self, file_ids: list[int]) -> CalculateStatsPayload:
        result = await self.db.execute(select(File).where(File.id.in_(file_ids)))
        files = result.scalars().all()

        total_counts = {str(d): 0 for d in range(10)}
        file_stats = []
        needs_commit = False

        for file in files:
            if file.content:
                if not file.digit_counts:
                    counts = self._count_digits(file.content)
                    file.digit_counts = counts
                    needs_commit = True
                else:
                    counts = file.digit_counts

                for digit, count in counts.items():
                    total_counts[digit] += count

                file_stats.append(
                    FileStatItemPayload(
                        file_id=file.id,
                        file_name=file.name,
                        counts=counts,
                    )
                )

        if needs_commit:
            await self.db.commit()

        return CalculateStatsPayload(
            total_statistics=total_counts, file_statistics=file_stats
        )
