from dataclasses import fields, is_dataclass
from typing import get_args, get_origin, get_type_hints


def convert_to_dataclass(cls, data):
    """Recursively convert dicts/lists to dataclass instances."""
    if isinstance(data, cls):
        return data
    if isinstance(data, dict):
        field_types = get_type_hints(cls)
        converted_data = {}
        for f in fields(cls):
            value = data.get(f.name)
            if value is None:
                converted_data[f.name] = None
                continue

            target_type = field_types.get(f.name)
            origin = get_origin(target_type)
            args = get_args(target_type)

            if f.name == "languages" and isinstance(value, list):
                converted_data[f.name] = [str(lang) for lang in value]
            elif origin is list and args:
                item_type = args[0]
                converted_list = []
                for item in value:
                    if is_dataclass(item_type) and isinstance(item, str):
                        converted_list.append(item_type(name=item))
                    else:
                        converted_list.append(convert_to_dataclass(item_type, item))
                converted_data[f.name] = converted_list
            elif is_dataclass(target_type):
                converted_data[f.name] = convert_to_dataclass(target_type, value)
            else:
                converted_data[f.name] = value

        return cls(**converted_data)
    return data
