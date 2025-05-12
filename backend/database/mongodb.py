from typing import Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError

from backend.app.config import app_configuration
from backend.utils.logger import logger

# Module-level connection cache
_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    """
    Create and return a MongoDB client using configuration from app_configuration.
    If the client does not exist, it will be created.
    """
    global _client

    if _client is not None:
        return _client

    mongo_uri = getattr(app_configuration, "MONGO_URI", None)
    if not mongo_uri:
        raise EnvironmentError("MONGO_URI is not set in the configuration.")

    timeout_ms = getattr(app_configuration, "MONGO_CONNECTION_TIMEOUT_MS", 5000)

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=timeout_ms)
        # Verify connection with a ping
        _client.admin.command("ping")
        logger.info("Successfully connected to MongoDB.")
        return _client
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


def get_database() -> Database:
    """
    Get the configured MongoDB database instance.
    If the database does not exist, it will be created.
    """
    client = get_mongo_client()
    db_name = getattr(app_configuration, "MONGO_DB_NAME", None)
    if not db_name:
        raise EnvironmentError("MONGO_DB_NAME is not set in the configuration.")
    return client[db_name]


def get_collection(collection_name: Optional[str] = None) -> Collection:
    """
    Get a MongoDB collection by name. If no name is provided, use the default from config or fallback.
    If the collection does not exist, it will be created.
    """
    db = get_database()
    if not collection_name:
        collection_name = getattr(
            app_configuration, "FETCH_JOBS_COLLECTION", "fetch_jobs"
        )
    return db[collection_name]


def ensure_indexes(collection: Collection, indexes: list):
    """
    Ensure that the specified indexes exist on the collection.
    """
    for index in indexes:
        try:
            collection.create_index(index)
        except PyMongoError as e:
            logger.error(
                f"Failed to create index {index} on collection {collection.name}: {e}"
            )
