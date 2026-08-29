import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import DEV_SECRET_KEY, settings
from app.errors import (
    FieldValidationError,
    field_validation_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.ratelimit import limiter
from app.routers import (
    accounts,
    admin,
    auth,
    export_api,
    hr_api,
    import_api,
    manual_api,
    payments,
    registrations,
    rules_api,
    taxonomy_api,
    tournaments,
)
from app.scheduler import scheduler_loop

logger = logging.getLogger(__name__)


def _refuse_dev_secret_key() -> None:
    """Refuse to serve tokens signed with the published development key.

    A missing HEMA_SQUIRE_SECRET_KEY is silent by nature: everything works, and
    the only symptom is that anyone can mint a token for any account, Owner
    included. So it is a refusal to start rather than a warning, and debug mode
    — dev.sh and the test suite — is the single explicit exemption.
    """
    if settings.secret_key == DEV_SECRET_KEY and not settings.debug:
        raise RuntimeError(
            "HEMA_SQUIRE_SECRET_KEY is still the published development default. "
            "Set it (openssl rand -hex 32), or set HEMA_SQUIRE_DEBUG=1 for local work."
        )


def _warn_when_owner_unmatched() -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.models import Fencer

    if not settings.owner_email:
        logger.warning("HEMA_SQUIRE_OWNER_EMAIL is not set; no deployment Owner")
        return
    try:
        with Session(engine) as session:
            match = session.scalar(select(Fencer.id).where(Fencer.email == settings.owner_email))
        if match is None:
            logger.warning(
                "no account matches owner email %s; Owner capabilities are dormant",
                settings.owner_email,
            )
    except Exception:
        logger.exception("owner email check failed")


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
    _refuse_dev_secret_key()
    _warn_when_owner_unmatched()
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
    # slowapi reads the limiter off app.state and needs its own handler for the
    # 429; the decorated routes are in routers/auth.py
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(FieldValidationError, field_validation_error_handler)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(accounts.router)
    app.include_router(admin.router)
    app.include_router(tournaments.router)
    app.include_router(registrations.router)
    app.include_router(payments.router)
    app.include_router(rules_api.router)
    app.include_router(import_api.router)
    app.include_router(manual_api.router)
    app.include_router(export_api.router)
    app.include_router(hr_api.router)
    app.include_router(hr_api.ratings_router)
    app.include_router(taxonomy_api.router)
    return app


app = create_app()
