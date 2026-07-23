from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from src.exceptions import AppBaseException
from src.api.v1.router import router as api_v1_router
from src.config import settings
from src.services.target_api import TargetAPI

target_api_client = TargetAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.target_api = target_api_client
    yield
    await target_api_client.close()


app = FastAPI(
    title="FileDownloader API",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.exception_handler(AppBaseException)
async def custom_exception_handler(request, exc: AppBaseException):
    from src.schemas import BaseResponse

    return BaseResponse(error=True, message=exc.message, payload=None)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.api.HOST,
        port=settings.api.PORT,
        reload=True,
    )
