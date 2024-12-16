
def fullname(o: 'Any') -> str:
    """
    Get full qualified name of an instance.
    :param o: Object
    :return: The full qualified name of the instance
    """
    klass = o.__class__
    module = klass.__module__
    if module == 'builtins':
        return klass.__qualname__  # avoid outputs like 'builtins.str'
    return module + '.' + klass.__qualname__
