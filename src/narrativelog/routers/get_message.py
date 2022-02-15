from __future__ import annotations

__all__ = ["get_message"]

import http

import fastapi

from ..message import Message
from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.get("/messages/{id}", response_model=Message)
async def get_message(
    id: str,
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Get one message."""
    el_table = state.narrativelog_db.table

    # Find the message
    async with state.narrativelog_db.engine.connect() as connection:
        result = await connection.execute(
            el_table.select().where(el_table.c.id == id)
        )
        row = result.fetchone()

    if row is None:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"No message found with id={id}",
        )

    return Message.from_orm(row)
