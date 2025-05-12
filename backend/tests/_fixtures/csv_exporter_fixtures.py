import pytest


@pytest.fixture
def repo_export_data_simple():
    return [
        {
            "name": "Repo1",
            "fullName": "owner/repo1",
            "languages": ["Python", "JavaScript"],
            "mergeRequests": [
                {"authorName": "Alice", "title": "Fix bug"},
                {"authorName": "Bob", "title": None},
            ],
        },
        {
            "name": "Repo2",
            "fullName": "owner/repo2",
            "languages": ["Java"],
            "mergeRequests": [{"authorName": "Charlie", "title": "Improve docs"}],
        },
    ]


@pytest.fixture
def repo_data_special_chars():
    # Cyrillic characters (in Russian)
    return [
        {
            "name": "Репозиторий",  # repository
            "fullName": "владелец/репозиторий",  # owner/repository
            "languages": ["Python", "C++"],
            "mergeRequests": [
                {"authorName": "Иван", "title": "Исправить баг"}
            ],  # Ivan / Fix bug
        }
    ]


@pytest.fixture
def repo_data_empty():
    return []
