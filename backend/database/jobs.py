from typing import List, Optional

from bson import ObjectId
from pymongo import errors
from pymongo.collection import Collection
from pymongo.results import InsertOneResult, DeleteResult, UpdateResult
from strawberry import asdict

from backend.database.mongodb import get_collection, ensure_indexes
from backend.graphql.git_types import FetchJob
from backend.utils.db_utils import (
    validate_is_dataclass,
    convert_enums_to_strings,
    find_one_as_dict,
    convert_strings_to_enums,
)
from backend.utils.logger import logger


def _get_or_create_collection(collection_name: Optional[str] = None) -> Collection:
    """
    Get the MongoDB collection, create it if it does not exist and ensure indexes.
    """
    collection = get_collection(collection_name)
    # Ensure an index on jobId for fast lookups
    ensure_indexes(collection, [{"jobId": 1}])
    return collection


def create_job(job: FetchJob, collection: Optional[Collection] = None) -> str:
    """
    Create a new fetch job in the database.
    If no collection is provided, uses the default from config.
    """
    validate_is_dataclass(job, "job")
    db_collection = collection or _get_or_create_collection()

    try:
        job_dict = convert_enums_to_strings(asdict(job))
        new_id = ObjectId()

        # Ensure consistent IDs in both database and string formats
        job_dict |= {"_id": new_id, "jobId": str(new_id)}

        result: InsertOneResult = db_collection.insert_one(job_dict)
        if result.inserted_id != new_id:
            raise RuntimeError("Job ID mismatch during insertion")
        logger.info(f"Created new job with ID {new_id}")
        return str(new_id)
    except errors.PyMongoError as e:
        logger.error(f"Job creation failed: {e}")
        raise RuntimeError(f"Job creation failed: {e}") from e


def update_job(job: FetchJob, collection: Optional[Collection] = None) -> None:
    """
    Update existing job with new values.
    """
    validate_is_dataclass(job, "job")
    _validate_job_id(job.jobId)
    db_collection = collection or _get_or_create_collection()

    try:
        job_dict = convert_enums_to_strings(asdict(job))

        # Prevent modification of immutable identifiers
        immutable_fields = {"_id", "jobId"}
        update_data = {k: v for k, v in job_dict.items() if k not in immutable_fields}
        result: UpdateResult = db_collection.update_one(
            {"_id": ObjectId(job.jobId)}, {"$set": update_data}
        )
        if result.matched_count == 0:
            logger.warning(f"Job not found with ID: {job.jobId}")
            raise ValueError(f"Job not found with ID: {job.jobId}")
    except errors.PyMongoError as e:
        logger.error(f"Job update failed: {e}")
        raise RuntimeError(f"Job update failed: {e}") from e


def get_job(job_id: str, collection: Optional[Collection] = None) -> Optional[FetchJob]:
    """
    Retrieve a single job by ID.
    """
    _validate_job_id(job_id)
    db_collection = collection or _get_or_create_collection()

    try:
        document = find_one_as_dict(db_collection, {"_id": ObjectId(job_id)})
        return convert_strings_to_enums(document) if document else None
    except errors.PyMongoError as e:
        logger.error(f"Job retrieval failed: {e}")
        raise RuntimeError(f"Job retrieval failed: {e}") from e


def get_all_jobs(collection: Optional[Collection] = None) -> List[FetchJob]:
    """
    Retrieve all jobs from the collection.
    """
    db_collection = collection or _get_or_create_collection()

    try:
        return [convert_strings_to_enums(doc) for doc in db_collection.find()]
    except errors.PyMongoError as e:
        logger.error(f"Failed to retrieve jobs: {e}")
        raise RuntimeError(f"Failed to retrieve jobs: {e}") from e


def delete_job(job_id: str, collection: Optional[Collection] = None) -> bool:
    """
    Delete a job by ID.
    """
    _validate_job_id(job_id)
    db_collection = collection or _get_or_create_collection()

    try:
        result: DeleteResult = db_collection.delete_one({"_id": ObjectId(job_id)})
        if result.deleted_count > 0:
            logger.info(f"Deleted job with ID {job_id}")
        else:
            logger.warning(f"Tried to delete non-existent job with ID {job_id}")
        return result.deleted_count > 0
    except errors.PyMongoError as e:
        logger.error(f"Job deletion failed: {e}")
        raise RuntimeError(f"Job deletion failed: {e}") from e


def _is_valid_object_id(object_id: str) -> bool:
    """Check if string is a valid MongoDB ObjectId."""
    return ObjectId.is_valid(object_id)


def _validate_job_id(job_id: str) -> None:
    """Validate job ID format before database operations."""
    if not _is_valid_object_id(job_id):
        raise ValueError(f"Invalid job ID format: {job_id}")
