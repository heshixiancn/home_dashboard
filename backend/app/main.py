import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from .api import router
from .cache import cache
from .config import get_settings
from .database import SessionLocal
from .healthcheck import check_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scheduler() -> None:
    settings = get_settings()
    while True:
        try:
            await check_all(SessionLocal, settings.health_concurrency)
            cache.invalidate()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("scheduled health check failed")
        await asyncio.sleep(settings.check_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Home Service Dashboard", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

static_dir = Path(get_settings().static_dir)
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        target = static_dir / path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(static_dir / "index.html")

