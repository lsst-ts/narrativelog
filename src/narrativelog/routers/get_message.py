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
    message_table = state.narrativelog_db.message_table
    jira_fields_table = state.narrativelog_db.jira_fields_table

    async with state.narrativelog_db.engine.connect() as connection:
        # Find the message
        result_message = await connection.execute(
            message_table
            # Join with jira_fields_table
            .join(jira_fields_table)
            .select()
            .where(message_table.c.id == id)
        )
        row = result_message.fetchone()

        if row is None:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"No message found with id={id}",
            )

        return Message.model_validate(row)
