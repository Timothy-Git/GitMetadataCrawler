from datetime import datetime
from typing import List, Optional

import strawberry

from backend.graphql.enums import PlatformEnum, StateEnum, FetchJobMode


@strawberry.type(description="Represents a merge request in a repository.")
class MergeRequestData:
    authorName: Optional[str] = strawberry.field(
        default=None,
        description="The name of the author who created the merge request.",
    )
    createdAt: Optional[str] = strawberry.field(
        default=None, description="The creation date of the merge request."
    )
    description: Optional[str] = strawberry.field(
        default=None, description="The description or body of the merge request."
    )
    title: Optional[str] = strawberry.field(
        default=None, description="The title of the merge request."
    )


@strawberry.type(
    description="Represents a repository with its metadata and associated merge requests."
)
class RepoData:
    name: Optional[str] = strawberry.field(
        default=None, description="The name of the repository."
    )
    fullName: Optional[str] = strawberry.field(
        default=None,
        description="The full name of the repository, including the owner or namespace (e.g. 'owner/repo').",
    )
    description: Optional[str] = strawberry.field(
        default=None, description="The description of the repository."
    )
    starCount: Optional[int] = strawberry.field(
        default=None, description="The number of stars the repository has received."
    )
    createdAt: Optional[str] = strawberry.field(
        default=None, description="The creation date of the repository."
    )
    updatedAt: Optional[str] = strawberry.field(
        default=None, description="The last update date of the repository."
    )
    languages: Optional[List[str]] = strawberry.field(
        default=None,
        description="A list of programming languages used in the repository.",
    )
    mergeRequests: List[MergeRequestData] = strawberry.field(
        default=None,
        description="A list of merge requests associated with the repository.",
    )


@strawberry.input(description="Input type for fetcher settings.")
class FetcherSettingsInput:
    repoCount: int = strawberry.field(
        description="The number of repositories to fetch."
    )
    maxMRs: int = strawberry.field(
        description="The maximum number of merge requests to fetch per repository."
    )
    searchTerm: str = strawberry.field(
        description="The search term to filter repositories."
    )
    programmingLanguage: str = strawberry.field(
        description="The programming language to filter repositories."
    )


@strawberry.type(description="Represents the settings used for fetching repositories.")
class FetcherSettings:
    repoCount: int = strawberry.field(
        description="The number of repositories to fetch."
    )
    maxMRs: int = strawberry.field(
        description="The maximum number of merge requests to fetch per repository."
    )
    searchTerm: str = strawberry.field(
        description="The search term to filter repositories."
    )
    programmingLanguage: str = strawberry.field(
        description="The programming language to filter repositories."
    )


@strawberry.type(description="Represents a fetch job with its metadata and results.")
class FetchJob:
    jobId: str = strawberry.field(
        description="The unique identifier of the fetch job. This is the same as in MongoDB."
    )
    name: str = strawberry.field(description="The name of the fetch job.")
    mode: FetchJobMode = strawberry.field(
        description="The mode in which the fetch job is executed. This influences how the request is generated."
    )
    platform: PlatformEnum = strawberry.field(
        description="The platform from which repositories are fetched."
    )
    state: StateEnum = strawberry.field(
        description="The current state of the fetch job."
    )
    startTime: Optional[datetime] = strawberry.field(
        default=None, description="The start time of the fetch job."
    )
    endTime: Optional[datetime] = strawberry.field(
        default=None, description="The end time of the fetch job."
    )
    executionTime: Optional[int] = strawberry.field(
        default=None,
        description="The total execution time of the fetch job in seconds.",
    )
    settings: Optional[FetcherSettings] = strawberry.field(
        default=None,
        description="The settings used for the fetch job. [Only in assistant mode]",
    )
    requestedFields: Optional[List[str]] = strawberry.field(
        default=None,
        description="The fields requested in the fetch job. [Only in assistant mode]",
    )
    rawQuery: Optional[str] = strawberry.field(
        default=None,
        description="The raw query used in expert mode. [Only in expert mode]",
    )
    repoData: List[RepoData] = strawberry.field(
        default=None, description="The list of repository data fetched by the job."
    )
    log: List[str] = strawberry.field(
        default_factory=list, description="The log messages of the job."
    )


@strawberry.input(description="Input type for updating an existing fetch job.")
class UpdateFetchJobInput:
    jobId: str = strawberry.field(
        description="The unique identifier of the fetch job to be updated."
    )
    name: Optional[str] = strawberry.field(
        default=None,
        description="The new name for the fetch job, if it needs to be updated.",
    )
    mode: Optional[FetchJobMode] = strawberry.field(
        default=None,
        description="The new mode for the fetch job, if it needs to be updated.",
    )
    platform: Optional[PlatformEnum] = strawberry.field(
        default=None,
        description="The platform for the fetch job, if it needs to be updated.",
    )
    fetcherSettings: Optional[FetcherSettingsInput] = strawberry.field(
        default=None, description="The updated fetcher settings for the fetch job."
    )
    requestedFields: Optional[List[str]] = strawberry.field(
        default=None,
        description="The updated list of requested fields for the fetch job.",
    )
    rawQuery: Optional[str] = strawberry.field(
        default=None,
        description="The updated raw query for the fetch job, if applicable.",
    )


@strawberry.input(description="Input type for specifying requested fields.")
class RequestedFieldInput:
    field: str = strawberry.field(description="The name of the requested field.")
    subfields: Optional[List[str]] = strawberry.field(
        default=None,
        description="A list of subfields associated with the requested field.",
    )


@strawberry.type(description="Represents a URL to the file generated by a plugin.")
class PluginUrl:
    name: str = strawberry.field(description="The name for the plugin generated file.")
    url: str = strawberry.field(
        description="The URL or file path to access the plugin generated file."
    )


@strawberry.type(description="Represents the result of a plugin execution.")
class PluginResult:
    urls: List[PluginUrl] = strawberry.field(
        description="A list of URLs or file paths generated by the plugin."
    )
    message: Optional[str] = strawberry.field(
        default=None,
        description="An optional message providing additional information about the plugin result.",
    )
