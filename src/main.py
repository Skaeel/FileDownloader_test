from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from src.exceptions import AppBaseException
from src.api.v1.router import api_v1_router
from src.config import settings

app = FastAPI(
    title="FileDownloader API",
    description="",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.exception_handler(AppBaseException)
async def custom_exception_handler(exc: AppBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "payload": None,
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api.HOST,
        port=settings.api.PORT,
        reload=True,
    )
