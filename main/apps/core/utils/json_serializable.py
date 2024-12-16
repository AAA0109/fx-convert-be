import json

from django.core.serializers.json import DjangoJSONEncoder


def is_json_serializable(value):
    try:
        json.dumps(value)
        return True
    except TypeError:
        return False


def _initialize_new_data(data):
    if isinstance(data, list):
        return []
    elif isinstance(data, set):
        return set()
    elif isinstance(data, tuple):
        return tuple()
    elif isinstance(data, dict):
        return {}
    else:
        raise TypeError("data must be a list, set, or tuple")


def _append_to_new_data(new_data, data, value, key=None):
    if isinstance(data, list):
        new_data.append(remove_non_json_serializable(value))
    elif isinstance(data, set):
        new_data.add(remove_non_json_serializable(value))
    elif isinstance(data, tuple):
        new_data = (*new_data, remove_non_json_serializable(value))
    elif isinstance(data, dict):
        new_data[key] = remove_non_json_serializable(data[value])
    else:
        raise TypeError("data must be a list, set, or tuple")
    return new_data


def _process(data, value, new_data, key=None):
    if is_json_serializable(value) or isinstance(value, (dict, set, list, tuple)):
        if key is None:
            new_data = _append_to_new_data(new_data, data, value)
        else:
            new_data[key] = remove_non_json_serializable(value)
    else:
        print(f"Removed non-serializable item: {key}: {value}")
    return new_data


def remove_non_json_serializable(data):
    if isinstance(data, (list, tuple, set, dict)):
        new_data = _initialize_new_data(data)
        if isinstance(data, dict):
            for key, value in data.items():
                new_data = _process(data, value, new_data, key)
        else:
            for value in data:
                new_data = _process(data, value, new_data, key=None)
        return new_data
    else:
        return data


def json_serializable(data):
    """Ensure data is JSON serializable"""
    try:
        json.dumps(data)
        return data
    except TypeError:
        if isinstance(data, dict):
            return {k: json_serializable(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return [json_serializable(item) for item in data]
        elif hasattr(data, '__dict__'):
            return json_serializable(data.__dict__)
        else:
            return str(data)
