import asyncio
import logging
import random

import httpx

from src.config import settings
from src.exceptions import AppBaseException

logger = logging.getLogger(__name__)


class TargetAPI:
    MAX_RETRIES = 5
    BASE_BACKOFF = 1.0
    MAX_BACKOFF = 60.0
    POLITE_DELAY = 0.3
    DELAY_429 = 1800

    def __init__(self):
        self.base_url = settings.target_api.target_api_url
        self.headers = {"x-candidate-id": settings.candidate.ID}

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        for attempt in range(self.MAX_RETRIES):
            try:
                delay = self.POLITE_DELAY + random.uniform(0.2, 0.8)
                await asyncio.sleep(delay)

                resp = await self.client.request(method, path, **kwargs)

                if resp.is_success:
                    return resp

                if resp.status_code == 429:
                    retry_after = self._parse_retry_after(resp)
                    wait_time = max(
                        retry_after, self.BASE_BACKOFF * (2**attempt)
                    ) + random.uniform(1.0, 2.5)

                    logger.warning(
                        f"Привышен лимит запросов. Ждём {wait_time:.1f}с. Попытка {attempt + 1}/{self.MAX_RETRIES}"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                if resp.status_code == 403:
                    wait_time = self.DELAY_429 + random.uniform(1.0, 2.5)
                    logger.warning(
                        f"Получен бан за частое нарушение лимитов. Ждем {wait_time}c."
                    )
                    await asyncio.sleep(wait_time)
                    continue

            except Exception:
                raise AppBaseException(message="Unknown Target API error")

    def _parse_retry_after(self, resp: httpx.Response) -> float:
        value = resp.headers.get("Retry-After", "3")
        if value.isdigit():
            return float(value)

    async def get_names(self) -> list[str]:
        resp = await self._request("GET", "/api/files/names")
        data = resp.json()
        return data.get("file_names", []) if data else []

    async def download(self, names: list[str]) -> list[bytes]:
        all_zips = []
        for i in range(0, len(names), 3):
            batch = names[i : i + 3]
            logger.info(f"📥 Скачиваю батч: {batch}")
            resp = await self._request(
                "POST", "/api/files/download", json={"file_names": batch}
            )
            all_zips.append(resp.content)
        return all_zips

    async def mark_downloaded(self, names: list[str]) -> dict:
        resp = await self._request(
            "POST", "/api/files/downloaded", json={"file_names": names}
        )
        return resp.json()

    async def close(self):
        await self.client.aclose()
