from __future__ import annotations

__all__ = ["delete_message"]

import http

import astropy.time
import fastapi
import sqlalchemy as sa

from ..shared_state import SharedState, get_shared_state

router = fastapi.APIRouter()


@router.delete("/messages/{id}", status_code=http.HTTPStatus.NO_CONTENT)
async def delete_message(
    id: str,
    state: SharedState = fastapi.Depends(get_shared_state),
) -> fastapi.Response:
    """Delete a message by marking it invalid.

    A no-op if already the message is already marked invalid.

    If the message is valid: set ``is_valid`` false and ``date_invalidated``
    to the current date.
    """
    current_tai = astropy.time.Time.now().tai.datetime

    message_table = state.narrativelog_db.message_table

    # Delete the message by setting date_invalidated to the current TAI time
    # (if not already set). Note: coalesce returns the first non-null
    # value from a list of values.
    async with state.narrativelog_db.engine.begin() as connection:
        result = await connection.execute(
            message_table.update()
            .where(message_table.c.id == id)
            .values(
                date_invalidated=sa.func.coalesce(
                    message_table.c.date_invalidated, current_tai
                )
            )
        )

    if result.rowcount == 0:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail=f"No message found with id={id}",
        )
    return fastapi.Response(status_code=http.HTTPStatus.NO_CONTENT)
