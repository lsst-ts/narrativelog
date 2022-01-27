from __future__ import annotations

__all__ = ["get_config"]

import fastapi
import pydantic

from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


class Config(pydantic.BaseModel):
    site_id: str = pydantic.Field(title="Site ID.")

    class Config:
        orm_mode = True


@router.get("/configuration", response_model=Config)
@router.get("/configuration/", response_model=Config, include_in_schema=False)
async def get_config(
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Config:
    """Get the configuration."""

    return Config.from_orm(state)
