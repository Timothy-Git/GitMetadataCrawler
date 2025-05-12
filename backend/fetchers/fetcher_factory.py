from backend.app.config import app_configuration
from backend.fetchers.base_fetcher import BaseFetcher
from backend.fetchers.graphql.github_fetcher import GitHubFetcher
from backend.fetchers.graphql.gitlab_fetcher import GitLabFetcher
from backend.fetchers.rest_api.bitbucket_fetcher import BitbucketFetcher
from backend.graphql.enums import PlatformEnum
from backend.utils.token_pool import TokenPool


class FetcherFactory:
    """Factory for creating fetcher instances for different platforms."""

    @staticmethod
    def get_fetcher(platform: PlatformEnum) -> BaseFetcher:
        """Return a new fetcher instance for the given platform."""
        if platform == PlatformEnum.GITHUB:
            return GitHubFetcher(
                base_url=app_configuration.GITHUB_BASE_URL,
                token_pool=TokenPool(app_configuration.github_tokens),
            )
        elif platform == PlatformEnum.GITLAB:
            return GitLabFetcher(
                base_url=app_configuration.GITLAB_BASE_URL,
                token_pool=TokenPool(app_configuration.gitlab_tokens),
            )
        elif platform == PlatformEnum.BITBUCKET:
            return BitbucketFetcher(base_url=app_configuration.BITBUCKET_BASE_URL)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
