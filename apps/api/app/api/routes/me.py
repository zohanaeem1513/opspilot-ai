import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_profile
from app.db.models.profile import Profile

router = APIRouter()


class MeResponse(BaseModel):
    id: uuid.UUID


@router.get("/me", response_model=MeResponse)
async def me(profile: Annotated[Profile, Depends(get_current_profile)]) -> MeResponse:
    return MeResponse(id=profile.id)
