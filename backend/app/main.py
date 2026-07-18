import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import (
    accounts,
    auth,
    import_api,
    payments,
    registrations,
    rules_api,
    taxonomy_api,
    tournaments,
)
from app.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task is not None:
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
    app.include_router(taxonomy_api.router)
    return app


app = create_app()
