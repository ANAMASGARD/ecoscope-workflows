from dataclasses import dataclass
from typing import Any, Annotated

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from ecoscope_workflows.annotations import AnyDataFrame
from ecoscope_workflows.decorators import task
from ecoscope_workflows.indexes import CompositeFilter, IndexName, IndexValue


def _groupkey_to_composite_filter(
    groupers: list[IndexName], index_values: tuple[IndexValue, ...]
) -> CompositeFilter:
    """Given the list of `groupers` used to group a dataframe, convert a group key
    tuple (the pandas native representation) to a composite filter (our representation).

    Examples:

    ```python
    >>> groupers = ["month", "year"]
    >>> index_values = (1, 2021)
    >>> _groupkey_to_composite_filter(groupers, index_values)
    (('month', '=', 1), ('year', '=', 2021))
    >>> groupers = ["animal_name", "species"]
    >>> index_values = ("Jo", "Elephas maximus")
    >>> _groupkey_to_composite_filter(groupers, index_values)
    (('animal_name', '=', 'Jo'), ('species', '=', 'Elephas maximus'))

    ```

    """
    return tuple((index, "=", value) for index, value in zip(groupers, index_values))


@dataclass(frozen=True)
class Grouper:
    index_name: IndexName
    display_name: str | SkipJsonSchema[None] = None
    help_text: str | SkipJsonSchema[None] = None


@task
def set_groupers(
    groupers: Annotated[
        list[Grouper],
        Field(
            description="""\
            Index(es) and/or column(s) to group by, along with
            optional display names and help text.
            """,
        ),
    ],
) -> Annotated[
    list[Grouper],
    Field(
        description="Passthrough of the input groupers, for use in downstream tasks."
    ),
]:
    return groupers


KeyedIterableOfDataFrames = list[tuple[CompositeFilter, AnyDataFrame]]
KeyedIterableOfAny = list[tuple[CompositeFilter, Any]]
CombinedKeyedIterable = list[tuple[CompositeFilter, list[Any]]]


@task
def split_groups(
    df: AnyDataFrame,
    groupers: Annotated[
        list[Grouper], Field(description="Index(es) and/or column(s) to group by")
    ],
) -> Annotated[
    KeyedIterableOfDataFrames,
    Field(
        description="""\
        List of 2-tuples of key:value pairs. Each key:value pair consists of a composite
        filter (the key) and the corresponding subset of the input dataframe (the value).
        """
    ),
]:
    # TODO: configurable cardinality constraint with a default?
    grouper_index_names = [g.index_name for g in groupers]
    grouped = df.groupby(grouper_index_names)
    return [
        (_groupkey_to_composite_filter(grouper_index_names, index_value), group)
        for index_value, group in grouped
    ]


@task
def groupbykey(
    iterables: Annotated[
        list[KeyedIterableOfAny], Field(description="List of keyed iterables")
    ],
) -> Annotated[
    CombinedKeyedIterable,
    Field(
        description="""
        Flattened collection of keyed iterables with values associated with matching keys combined.
        """
    ),
]:
    seen = set()
    out: dict[CompositeFilter, list] = {}
    for i in iterables:
        for key, value in i:
            if key in seen:
                out[key].append(value)
            else:
                seen.add(key)
                out[key] = [value]
    return list(out.items())
