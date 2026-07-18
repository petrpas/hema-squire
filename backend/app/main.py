import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import (
    accounts,
    auth,
    export_api,
    hr_api,
    import_api,
    payments,
    registrations,
    rules_api,
    taxonomy_api,
    tournaments,
)
from app.scheduler import scheduler_loop

logger = logging.getLogger(__name__)


def _populate_hr_index_if_empty() -> None:
    from sqlalchemy.orm import Session

    from app import hr_sync
    from app.db import engine

    try:
        with Session(engine) as session:
            outcome = hr_sync.ensure_index(session, hr_sync.get_hr_fetcher())
        if outcome is not None:
            logger.info("HR index auto-population: %s", outcome)
    except Exception:
        logger.exception("HR index auto-population failed; serving without it")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if settings.scheduler_enabled:
        tasks.append(asyncio.create_task(scheduler_loop()))
    if settings.hr_auto_refresh:
        # fresh deployment: fetch the fighters index in the background
        tasks.append(asyncio.create_task(asyncio.to_thread(_populate_hr_index_if_empty)))
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="HEMA Squire", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(accounts.router)
    app.include_router(tournaments.router)
    app.include_router(registrations.router)
    app.include_router(payments.router)
    app.include_router(rules_api.router)
    app.include_router(import_api.router)
    app.include_router(export_api.router)
    app.include_router(hr_api.router)
    app.include_router(hr_api.ratings_router)
    app.include_router(taxonomy_api.router)
    return app


app = create_app()
