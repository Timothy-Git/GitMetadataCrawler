from enum import Enum

import strawberry


@strawberry.enum(
    description="Represents the supported platforms for fetching repositories."
)
class PlatformEnum(Enum):
    GITHUB = strawberry.enum_value(
        "GitHub", description="The GitHub platform for fetching repositories."
    )
    GITLAB = strawberry.enum_value(
        "GitLab", description="The GitLab platform for fetching repositories."
    )
    BITBUCKET = strawberry.enum_value(
        "Bitbucket", description="The Bitbucket platform for fetching repositories."
    )


@strawberry.enum(description="Represents the possible states of a fetch job.")
class StateEnum(Enum):
    CREATED = strawberry.enum_value(
        "Created", description="The fetch job has been created but not started yet."
    )
    RUNNING = strawberry.enum_value(
        "Running", description="The fetch job is currently in progress."
    )
    SUCCESSFUL = strawberry.enum_value(
        "Successful", description="The fetch job completed successfully."
    )
    STOPPED = strawberry.enum_value(
        "Stopped", description="The fetch job was stopped manually."
    )
    FAILURE = strawberry.enum_value(
        "Failure", description="The fetch job failed due to an error."
    )


@strawberry.enum(
    description="Represents the modes in which a fetch job can be executed."
)
class FetchJobMode(Enum):
    ASSISTANT = strawberry.enum_value(
        "Assistant",
        description="Assistant mode for guided fetch operations. "
        "Job requires 'settings' and 'requestedFields'.",
    )
    EXPERT = strawberry.enum_value(
        "Expert",
        description="Expert mode for advanced fetch operations. "
        "Job requires 'rawQuery'.",
    )


@strawberry.enum(description="Represents the log levels.")
class LogLevel(Enum):
    DEBUG = strawberry.enum_value("Debug", description="Debug-level log messages.")
    INFO = strawberry.enum_value("Info", description="Informational log messages.")
    WARNING = strawberry.enum_value(
        "Warning", description="Warning-level log messages."
    )
    ERROR = strawberry.enum_value("Error", description="Error-level log messages.")
    EXCEPTION = strawberry.enum_value(
        "Exception", description="Exception-level log messages."
    )


class DataType(Enum):
    """
    Internally represents the supported data types for the mapping process in fetchers.
    """

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
