from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from the .env file
load_dotenv()


class AppConfiguration(BaseSettings):
    """Application configuration with environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Server Configuration
    SERVER_HOST: str = Field(
        default="127.0.0.1", description="Host address for the server"
    )
    SERVER_PORT: int = Field(
        default=5000, ge=1, le=65535, description="Port number for the server"
    )

    # Platform Configurations
    GITLAB_BASE_URL: str = Field(
        default="https://gitlab.com/api/graphql",
        description="Base URL for GitLab GraphQL API",
    )
    GITLAB_TOKENS: str = Field(
        default="", description="Comma-separated GitLab personal access tokens"
    )

    GITHUB_BASE_URL: str = Field(
        default="https://api.github.com/graphql",
        description="Base URL for GitHub GraphQL API",
    )
    GITHUB_TOKENS: str = Field(
        default="", description="Comma-separated GitHub personal access tokens"
    )

    EXPORT_PATH: str = Field(
        default=None, description="Directory for exported CSV files"
    )

    BITBUCKET_BASE_URL: str = Field(
        default="https://api.bitbucket.org/2.0",
        description="Base URL for Bitbucket REST API",
    )

    # Bitbucket OAuth2 Configuration
    BITBUCKET_CLIENT_ID: str = Field(description="Bitbucket OAuth2 client ID")
    BITBUCKET_SECRET: str = Field(description="Bitbucket OAuth2 client secret")
    BITBUCKET_TOKEN_URL: str = Field(
        default="https://bitbucket.org/site/oauth2/access_token",
        description="URL for Bitbucket OAuth2 token endpoint",
    )

    # Network Configuration
    DEFAULT_TIMEOUT: float = Field(
        default=180.0, ge=1.0, description="Default HTTP request timeout in seconds"
    )
    REQUEST_DELAY: float = Field(
        default=1.0,
        ge=0.0,
        description="Default delay between consecutive requests in seconds",
    )
    MAX_RETRIES: int = Field(
        default=5, ge=1, description="Maximum retry attempts for rate-limited requests"
    )
    BACKOFF_FACTOR: float = Field(
        default=1.0,
        ge=0.1,
        description="Multiplier for exponential delay between retries",
    )
    BACKOFF_MIN: int = Field(
        default=2,
        ge=1,
        description="Minimum backoff time for exponential retry in seconds",
    )
    BACKOFF_MAX: int = Field(
        default=8,
        ge=1,
        description="Maximum backoff time for exponential retry in seconds",
    )
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=10, ge=1, description="Maximum simultaneous HTTP requests allowed"
    )
    USER_AGENT: str = Field(
        default="Project/1.0 (+https://example.com/contact)",
        description=(
            "Client identification for API requests. "
            "Should follow format: <product>/<version> (+<contact-info>)"
        ),
    )

    # Database Configuration
    MONGO_URI: str = Field(description="MongoDB connection URI")
    MONGO_DB_NAME: str = Field(description="Default database name")
    FETCH_JOBS_COLLECTION: str = Field(
        default="fetch_jobs", description="Collection name for storing fetch jobs"
    )

    # REST Fetcher Configuration
    RESULTS_KEY: str = Field(
        default="values", description="JSON key containing paginated results"
    )
    PAGE_SIZE: int = Field(
        default=100,
        ge=1,
        description="Default number of items per page for REST API pagination",
    )
    LINK_HEADER: bool = Field(
        default=True, description="Whether to use RFC 5988 link headers for pagination"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Application log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)",
    )

    TOKEN_BAN_COOLDOWN: int = Field(
        default=600,  # 10 minutes
        ge=1,
        description="Cooldown in seconds for banned tokens before they are available again",
    )

    @property
    def github_tokens(self) -> List[str]:
        return [
            t.strip().strip('"').strip("'")
            for t in self.GITHUB_TOKENS.split(",")
            if t.strip()
        ]

    @property
    def gitlab_tokens(self) -> List[str]:
        return [
            t.strip().strip('"').strip("'")
            for t in self.GITLAB_TOKENS.split(",")
            if t.strip()
        ]


app_configuration = AppConfiguration()
