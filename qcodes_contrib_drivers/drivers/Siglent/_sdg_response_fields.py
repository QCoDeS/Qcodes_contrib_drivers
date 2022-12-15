from itertools import takewhile
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Optional,
    Tuple,
    TypeVar,
)

T = TypeVar("T")


def identity(x: T) -> T:
    return x


def group_by_two(list_: Iterable[T]) -> Iterator[Tuple[T, T]]:
    return zip(*2 * (iter(list_),))


def iter_str_split(string: str, *, sep: str, start: int = 0) -> Iterator[str]:
    if slen := len(sep):
        last: int = start
        while (next := string.find(sep, last)) != -1:
            yield string[last:next]
            last = next + slen
        yield string[last:]
    else:
        yield from iter(string)


def find_first_by_key(
    search_key: str,
    items: Iterator[Tuple[str, str]],
    *,
    transform_found: Callable[[str], Any] = identity,
    not_found=None,
) -> Any:
    for k, value in items:
        if k == search_key:
            return transform_found(value)
    else:
        return not_found


def substr_from(_n, /, *, then=identity) -> Callable[[str], Any]:
    if then is identity:
        return lambda _s: _s[_n:]
    return lambda str: then(str[_n:])


def none_to_empty_str(value):
    return "" if value is None else value


def strip_unit(
    _suffix: str, /, *, then: Callable[[str], Any] = identity
) -> Callable[[str], Any]:
    if then is identity:
        return lambda _s: _s.removesuffix(_suffix)

    return lambda _s: then(_s.removesuffix(_suffix))

def _merge_dicts_newpy(*dicts: dict) -> dict:
    dest = dict()
    for src in dicts:
        dest |= src
    return dest

def _merge_dicts_oldpy(*dicts: dict) -> dict:
    if not len(dict):
        return dict()
    dicts = iter(dicts)
    dest = dict(next(dicts))
    for src in dicts:
        for k, v in src.items():
            dest[k] = v
    return dest

try:
    {} | {}
    merge_dicts = _merge_dicts_newpy
except TypeError:
    merge_dicts = _merge_dicts_oldpy
    del _merge_dicts_newpy

def extract_oddfirst_field(
    result_prefix_len: int,
    name: Optional[str],
    *,
    then: Callable[[str], Any] = identity,
    else_default=None,
) -> Callable[[str], Any]:
    def result_func(response: str):
        response_items = iter_str_split(response, start=result_prefix_len, sep=",")
        first = next(response_items)
        if name is None:
            return then(first)
        else:
            return find_first_by_key(
                name,
                group_by_two(response_items),
                transform_found=then,
                not_found=else_default,
            )

    return result_func


def extract_first_state_or_group_prefixed_field(
    _result_prefix_len: int,
    name: str,
    *,
    then: Callable[[str], Any] = identity,
    else_default=None,
) -> Callable[[str], Any]:
    def result_func(response: str):
        response_items = iter_str_split(response, start=_result_prefix_len, sep=",")

        try:
            # STATE ON/OFF
            state_key, state_value = next(response_items), next(response_items)
        except StopIteration:
            return else_default

        if name == state_key:
            return then(state_value)

        param_group, param_name = name.split(",")

        # <AM|FM|PM|PWM... etc> / <CARR>
        for group in response_items:
            if group == param_group:
                break
        else:
            return else_default

        return find_first_by_key(
            param_name,
            group_by_two(response_items),
            transform_found=then,
            not_found=else_default,
        )

    return result_func


# ---------------------------------------------------------------


def extract_regular_field(
    result_prefix_len: int,
    name: str,
    *,
    then: Callable[[str], Any] = identity,
    else_default=None,
) -> Callable[[str], Any]:
    def result_func(response: str):
        return find_first_by_key(
            name,
            group_by_two(iter_str_split(response, start=result_prefix_len, sep=",")),
            transform_found=then,
            not_found=else_default,
        )

    return result_func


# ---------------------------------------------------------------


def extract_X_or_non_X_field(
    _X: str,
    _result_prefix_len,
    name: str,
    *,
    then: Callable[[str], Any] = identity,
    else_default=None,
) -> Callable[[str], Any]:

    if not name.startswith(_X + ","):

        def result_func(response: str):
            items = takewhile(
                lambda str: str != _X,
                iter_str_split(response, start=_result_prefix_len, sep=","),
            )

            return find_first_by_key(
                name,
                group_by_two(items),
                transform_found=then,
                not_found=else_default,
            )

    else:
        name = name[len(_X) + 1 :]

        def result_func(response: str):
            items = iter_str_split(response, start=_result_prefix_len, sep=",")

            for item in items:
                if item == _X:
                    break
            else:
                return else_default

            return find_first_by_key(
                name,
                group_by_two(items),
                transform_found=then,
                not_found=else_default,
            )

    return result_func
