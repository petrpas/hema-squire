from fastapi import APIRouter

from app.taxonomy import DISCIPLINES

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("/disciplines")
def discipline_taxonomy() -> dict[str, str]:
    return DISCIPLINES
