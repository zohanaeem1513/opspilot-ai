from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.session import ping_database

router = APIRouter()


class ReadyResponse(BaseModel):
    status: str
    database: str


async def get_database_ping() -> Callable[[], Awaitable[None]]:
    """FastAPI dependency seam — tests override this to mock connectivity
    without touching a real database."""
    return ping_database


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"description": "Database unreachable or not configured"}},
)
async def ready(
    ping: Annotated[Callable[[], Awaitable[None]], Depends(get_database_ping)],
) -> ReadyResponse:
    try:
        await ping()
    except Exception as exc:
        # Never leak DATABASE_URL, credentials, or driver exception details to the client.
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return ReadyResponse(status="ok", database="ok")
