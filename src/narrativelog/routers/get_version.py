__all__ = ["get_version"]

import fastapi
import pydantic

from .. import __version__
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


class Version(pydantic.BaseModel):
    version: str = pydantic.Field(title="Current version of the REST API.")

    class Config:
        orm_mode = True
        from_attributes = True


@router.get("/version", response_model=Version)
@router.get("/version/", response_model=Version, include_in_schema=False)
async def get_version(
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Version:
    """Get the current version of the package."""

    return Version(version=__version__)
