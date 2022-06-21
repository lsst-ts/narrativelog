import fastapi
import fastapi.responses
import starlette.requests

from . import shared_state
from .routers import (
    add_message,
    delete_message,
    edit_message,
    find_messages,
    get_configuration,
    get_message,
)

app = fastapi.FastAPI()

subapp = fastapi.FastAPI(
    title="Narrative log service",
    description="A REST web service to create and manage "
    "operator-generated log messages.",
)
app.mount("/narrativelog", subapp)

subapp.include_router(add_message.router)
subapp.include_router(delete_message.router)
subapp.include_router(edit_message.router)
subapp.include_router(find_messages.router)
subapp.include_router(get_configuration.router)
subapp.include_router(get_message.router)


@subapp.get("/", response_class=fastapi.responses.HTMLResponse)
async def root(request: starlette.requests.Request) -> str:
    return f"""<html>
    <head>
        <title>
            Narrative log service
        </title>
    </head>
    <body>
        <h1>Narrative log service</h1>
        <p>Create and manage log messages.</p>
        <p><a href="{request.url}docs">Interactive OpenAPI documentation</a></p>
    </html>
    """


@app.on_event("startup")
async def startup_event() -> None:
    await shared_state.create_shared_state()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await shared_state.delete_shared_state()
