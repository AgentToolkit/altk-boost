import functools
from typing import Callable, List, TypeVar, Any


def flatten(arr_arr):
    return [b for bs in arr_arr for b in bs]


def break_array_into_chunks(arr: List, chunk_size: int) -> List[List[Any]]:
    res = []
    for i, v in enumerate(arr):
        if i % chunk_size == 0:
            cur = []
            res.append(cur)
        cur.append(v)
    return res


def sum(array):
    return functools.reduce(lambda a, b: a + b, array) if len(array) > 0 else 0


T = TypeVar("T")


def find(array: List[T], pred: Callable[[T], bool]):
    for item in array:
        if pred(item):
            return item


# remove duplicates and preserve ordering
T = TypeVar("T")


def remove_duplicates(array: List[T]) -> List[T]:
    res = []
    visited = set()
    for item in array:
        if item not in visited:
            res.append(item)
            visited.add(item)
    return res


def not_none(array: List[T]) -> List[T]:
    return [item for item in array if item is not None]


def split_array(arr: List[T], delimiter: T) -> List[List[T]]:
    result = []
    temp = []
    for item in arr:
        if item == delimiter:
            if temp:  # Avoid adding empty lists
                result.append(temp)
            temp = []
        else:
            temp.append(item)
    if temp:  # Add the last group if not empty
        result.append(temp)
    return result
