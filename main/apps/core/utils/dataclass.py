from dataclasses import fields
from typing import TypeVar, Type, Dict, Any

T = TypeVar('T')


def filter_dict_for_dataclass(cls: Type[T], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter a dictionary to only include keys that match the fields of a dataclass.

    :param cls: The dataclass type
    :param data: The dictionary to filter
    :return: A new dictionary with only the keys that match the dataclass fields
    """
    valid_fields = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in valid_fields}
