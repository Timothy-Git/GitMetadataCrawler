import uvicorn
from fastapi import FastAPI

from backend.app.config import app_configuration
from backend.graphql.router import graphql_router, file_router
from backend.utils.logger import logger

# Initialize FastAPI
app = FastAPI()

# Include GraphQL routes
app.include_router(graphql_router, prefix="/graphql")

# Include file download routes
app.include_router(file_router)

# Start the application only if executed directly
if __name__ == "__main__":
    logger.info(
        f"Starting server on http://{app_configuration.SERVER_HOST}:{app_configuration.SERVER_PORT}/graphql ..."
    )
    uvicorn.run(
        "main:app",
        host=app_configuration.SERVER_HOST,
        port=app_configuration.SERVER_PORT,
        reload=True,
    )
