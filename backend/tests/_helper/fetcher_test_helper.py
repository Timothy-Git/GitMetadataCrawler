class FetcherTestHelper:
    """Common helper methods for fetcher unit tests."""

    def _assert_repo_data(self, actual_repo, expected_repo):
        assert actual_repo.name == expected_repo.name, (
            f"Repository name mismatch: expected '{expected_repo.name}', got '{actual_repo.name}'."
        )
        if hasattr(expected_repo, "description"):
            assert actual_repo.description == expected_repo.description, (
                f"Description mismatch: expected '{expected_repo.description}', got '{actual_repo.description}'."
            )
        if hasattr(expected_repo, "starCount"):
            assert actual_repo.starCount == expected_repo.starCount, (
                f"Star count mismatch: expected '{expected_repo.starCount}', got '{actual_repo.starCount}'."
            )
        if (
            hasattr(expected_repo, "languages")
            and expected_repo.languages
            and actual_repo.languages
        ):
            assert actual_repo.languages == expected_repo.languages, (
                f"Language mismatch: expected '{expected_repo.languages}', got '{actual_repo.languages}'."
            )
        if (
            hasattr(expected_repo, "mergeRequests")
            and expected_repo.mergeRequests
            and actual_repo.mergeRequests
        ):
            assert (
                actual_repo.mergeRequests[0].authorName
                == expected_repo.mergeRequests[0].authorName
            ), (
                f"Merge request author mismatch: expected '{expected_repo.mergeRequests[0].authorName}', "
                f"got '{actual_repo.mergeRequests[0].authorName}'."
            )

    async def _fetch_and_validate_projects(
        self,
        fetcher,
        settings,
        fields,
        expected_count,
        expected_repo_name,
        mock_make_request,
        expected_star_count=50,
        expected_language="Python",
    ):
        """Helper to fetch and validate repository projects."""
        result = await fetcher.fetch_projects(settings, fields)
        assert len(result) == expected_count, (
            f"Expected {expected_count} repository(-ies), but got {len(result)}."
        )
        if expected_count > 0:
            repo = result[0]
            assert repo.name == expected_repo_name, (
                f"Expected repository name '{expected_repo_name}', got '{repo.name}'."
            )
            if expected_star_count is not None and hasattr(repo, "starCount"):
                assert repo.starCount == expected_star_count, (
                    "Star count mismatch in the repository."
                )
            # Ensure languages are compared as strings
            if hasattr(repo, "languages"):
                if isinstance(repo.languages, list):
                    actual_languages = [
                        lang if isinstance(lang, str) else lang.get("name", "")
                        for lang in repo.languages
                    ]
                else:
                    actual_languages = (
                        [repo.languages.get("name", "")]
                        if isinstance(repo.languages, dict)
                        else []
                    )
                assert expected_language in actual_languages, (
                    f"Expected '{expected_language}' as the primary language, got '{actual_languages}'."
                )
            if hasattr(repo, "mergeRequests"):
                assert len(repo.mergeRequests) == 1, (
                    "Mismatch in the number of merge requests."
                )
