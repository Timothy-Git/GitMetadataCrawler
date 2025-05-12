import os
from tempfile import gettempdir

from fastapi import APIRouter
from fastapi.responses import FileResponse
from strawberry.fastapi import GraphQLRouter

from backend.graphql.schema import schema

# GraphQL Router with defined schema
graphql_router = GraphQLRouter(schema)

# File download router
file_router = APIRouter()


@file_router.get("/files/{file_name}")
async def download_file(file_name: str):
    """
    Endpoint to download a file from the server.
    """
    file_path = os.path.join(gettempdir(), file_name)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path, media_type="text/csv", filename=file_name)
