from dataclasses import is_dataclass
from typing import Any, Optional

from backend.graphql.enums import PlatformEnum, StateEnum, FetchJobMode
from backend.graphql.git_types import FetcherSettings, FetchJob


def validate_is_dataclass(instance: Any, name: str) -> None:
    """Verify input is a dataclass instance."""
    if not is_dataclass(instance):
        raise TypeError(f"Expected dataclass for '{name}', got {type(instance).__name__}")


def remove_object_id(document: dict) -> dict:
    """Remove MongoDB identifier from document."""
    document.pop('_id', None)
    return document


def convert_enums_to_strings(data: dict) -> dict:
    """Convert enum values to their string representations."""
    if not isinstance(data, dict):
        raise TypeError(f"Invalid input type: {type(data).__name__}")

    conversions = {
        'platform': PlatformEnum,
        'state': StateEnum,
        'mode': FetchJobMode
    }

    for key, enum in conversions.items():
        if value := data.get(key):
            data[key] = value.value if isinstance(value, enum) else value

    return data


def convert_strings_to_enums(data: dict) -> FetchJob:
    """Restore enum objects from string values."""
    try:
        data = data.copy()
        data.pop('_id', None)

        enum_map = {
            'platform': PlatformEnum,
            'state': StateEnum,
            'mode': FetchJobMode
        }

        for key, enum in enum_map.items():
            if key in data and isinstance(data[key], str):
                normalized = data[key].upper()
                if normalized in enum.__members__:
                    data[key] = enum[normalized]
                else:
                    valid = ", ".join(enum.__members__)
                    raise ValueError(f"Invalid {key}: {data[key]}. Valid: {valid}")

        if settings := data.get('settings'):
            data['settings'] = FetcherSettings(**settings)

        return FetchJob(**data)
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Data conversion failed: {e}") from e


def find_one_as_dict(collection, query: dict) -> Optional[dict]:
    """Retrieve single document as dictionary."""
    if result := collection.find_one(query):
        return dict(result)
    return None
