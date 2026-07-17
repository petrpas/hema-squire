from fastapi import FastAPI

from app.routers import accounts, auth, registrations, taxonomy_api, tournaments


def create_app() -> FastAPI:
    app = FastAPI(title="HEMA Squire")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(accounts.router)
    app.include_router(tournaments.router)
    app.include_router(registrations.router)
    app.include_router(taxonomy_api.router)
    return app


app = create_app()
