from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.logging_conf import setup_logging
from app.scheduler.setup import start_scheduler, stop_scheduler

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="PSX Shariah Analyzer", lifespan=lifespan)
app.include_router(router)
