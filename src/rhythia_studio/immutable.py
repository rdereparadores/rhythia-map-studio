"""Read-only JSON containers for sharing analysis across cache/history/workers.

These are ordinary dict/list subclasses for JSON and NumPy interoperability.
Normal mutation fails immediately rather than silently changing old snapshots.
"""


def _read_only(*args, **kwargs):
    raise TypeError("Analysis is read-only; create a new analysis instead.")


class FrozenDict(dict):
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _read_only

    def __deepcopy__(self, memo):
        return self


class FrozenList(list):
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = _read_only
    reverse = sort = __iadd__ = __imul__ = _read_only

    def __deepcopy__(self, memo):
        return self


def freeze(value):
    """Copy mutable containers once, then safely reuse already-frozen values."""
    if isinstance(value, (FrozenDict, FrozenList)):
        return value
    if isinstance(value, dict):
        return FrozenDict((key, freeze(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return FrozenList(freeze(item) for item in value)
    return value
