"""Module D — record shapers (pure).

Turn raw payloads (v12 ``Metrics()`` JSON ``value`` list; v11 cellset) into the
unified record dicts the service returns. Two orientations:

- *gauge-long* (``by_cube``, ``by_server``): one row per metric, with
  ``Metric``/``Value``/``Unit``.
- *entity-wide* (``by_rule`` and the v11-only entity categories): one row per
  entity with heterogeneous attribute columns.

Values are passed through verbatim — never converted (ADR 0002).
"""

import itertools
from typing import Dict, List

from TM1py.Metrics.mdx import v11_entity_spec, v11_spec
from TM1py.Metrics.vocabulary import (
    CATEGORY_BY_CUBE,
    CATEGORY_BY_SERVER,
    ENTITY_DIM_COLUMN,
    entity_measure_columns,
    normalize_v11_measure,
)

DEFAULT_TIME_INTERVAL = "LATEST"

# Name prefix that selects a category's rows out of the flat v12 Metrics() list.
_V12_PREFIX = {
    CATEGORY_BY_CUBE: "cube_",
    CATEGORY_BY_SERVER: "replica_",
}


def shape_v12_gauge_records(raw: List[Dict], category: str) -> List[Dict]:
    """Shape raw v12 ``Metrics()`` rows into gauge-long records for ``category``.

    Selects only the rows whose ``Name`` belongs to the category
    (``cube_*`` for ``by_cube``, ``replica_*`` for ``by_server``). On v12 the
    metric name is canonical verbatim, so ``NativeName == Metric``. ``CubeName``
    is included for ``by_cube`` only.

    :raises KeyError: if ``category`` is not a gauge category.
    """
    try:
        prefix = _V12_PREFIX[category]
    except KeyError:
        raise KeyError(f"Unknown gauge Stats Category: '{category}'")

    include_cube = category == CATEGORY_BY_CUBE

    records: List[Dict] = []
    for row in raw:
        name = row.get("Name", "")
        if not name.startswith(prefix):
            continue

        record: Dict = {"Category": category}
        if include_cube:
            record["CubeName"] = row.get("CubeName")
        record["Metric"] = name
        record["NativeName"] = name
        record["Value"] = row.get("Value")
        record["Unit"] = row.get("Unit")
        record["ReplicaID"] = row.get("ReplicaID", 0)
        record["TimeInterval"] = DEFAULT_TIME_INTERVAL
        record["Timestamp"] = row.get("Timestamp")
        record["DatabaseName"] = row.get("DatabaseName")
        record["DatabaseID"] = row.get("DatabaseID")
        records.append(record)

    return records


def _dimension_of(member: Dict) -> str:
    """Extract the dimension name from a member's ``UniqueName``.

    ``[}PerfCubes].[}PerfCubes].[plan_BudgetPlan]`` -> ``}PerfCubes``.
    """
    unique = member["UniqueName"]
    return unique.split("].[", 1)[0].lstrip("[")


def shape_v11_gauge_records(cellset: Dict, category: str) -> List[Dict]:
    """Shape a raw v11 ``}Stats*`` cellset into gauge-long records for ``category``.

    Members are mapped to their dimension via ``UniqueName`` (the context/time
    axis ordinal is not fixed across queries), then each cell becomes one
    record: the measure is normalized to its canonical ``Metric``/``Unit`` via
    the vocabulary, the entity (cube) and time bucket are read from their
    dimensions. ``ReplicaID`` is always ``0`` on v11. Values are passed through
    verbatim (including ``None``).

    Note: v11 surfaces the MDX ``WHERE`` slicer as an axis in the cellset
    response (verified on a live 11.8 server), so the ``}TimeIntervals`` bucket
    — ``LATEST``, a specific bucket, or the full window — is always present on
    an axis and read per-row. ``DEFAULT_TIME_INTERVAL`` is only a safety
    fallback for the (unobserved) case where it is absent.

    :raises KeyError: if ``category`` is not a gauge category.
    """
    spec = v11_spec(category)
    measure_dim = spec["measure_dim"]
    entity_dim = spec["entity_dim"]
    time_dim = spec["time_dim"]

    axes = sorted(cellset.get("Axes", []), key=lambda a: a["Ordinal"])
    sizes = [len(axis["Tuples"]) for axis in axes]
    if any(size == 0 for size in sizes):
        return []

    # Pre-resolve each tuple on each axis into {dimension: member_name}.
    axis_tuples = [[{_dimension_of(m): m["Name"] for m in tup["Members"]} for tup in axis["Tuples"]] for axis in axes]
    cells = cellset.get("Cells", [])

    records: List[Dict] = []
    for coord in itertools.product(*(range(size) for size in sizes)):
        # OData cell ordinal: axis 0 varies fastest.
        index = 0
        factor = 1
        for axis_i, member_i in enumerate(coord):
            index += member_i * factor
            factor *= sizes[axis_i]

        dims: Dict[str, str] = {}
        for axis_i, member_i in enumerate(coord):
            dims.update(axis_tuples[axis_i][member_i])

        metric, native_name, unit = normalize_v11_measure(category, dims[measure_dim])
        value = cells[index].get("Value") if index < len(cells) else None

        record: Dict = {"Category": category}
        if entity_dim:
            record["CubeName"] = dims.get(entity_dim)
        record["Metric"] = metric
        record["NativeName"] = native_name
        record["Value"] = value
        record["Unit"] = unit
        record["ReplicaID"] = 0
        record["TimeInterval"] = dims.get(time_dim, DEFAULT_TIME_INTERVAL)
        record["Timestamp"] = None
        records.append(record)

    return records


def _axis_tuples_by_dimension(axes: List[Dict]) -> List[List[Dict[str, str]]]:
    """Pre-resolve each tuple on each axis into ``{dimension: member_name}``."""
    return [[{_dimension_of(m): m["Name"] for m in tup["Members"]} for tup in axis["Tuples"]] for axis in axes]


def shape_v11_entity_records(cellset: Dict, category: str) -> List[Dict]:
    """Shape a raw v11 ``}Stats*`` cellset into entity-wide records for ``category``.

    One row per entity (e.g. per ``(CubeName, LineNumber)`` for ``by_rule``);
    each of the category's measures becomes a column. Members are mapped to
    their dimension via ``UniqueName``. ``ReplicaID`` is always ``0`` on v11.

    :raises KeyError: if ``category`` is not an entity category.
    """
    spec = v11_entity_spec(category)
    measure_dim = spec["measure_dim"]
    entity_dims = spec["entity_dims"]
    time_dim = spec["time_dim"]
    measure_columns = entity_measure_columns(category)

    axes = sorted(cellset.get("Axes", []), key=lambda a: a["Ordinal"])
    sizes = [len(axis["Tuples"]) for axis in axes]
    if any(size == 0 for size in sizes):
        return []

    axis_tuples = _axis_tuples_by_dimension(axes)
    cells = cellset.get("Cells", [])

    records: Dict[tuple, Dict] = {}
    for coord in itertools.product(*(range(size) for size in sizes)):
        index = 0
        factor = 1
        for axis_i, member_i in enumerate(coord):
            index += member_i * factor
            factor *= sizes[axis_i]

        dims: Dict[str, str] = {}
        for axis_i, member_i in enumerate(coord):
            dims.update(axis_tuples[axis_i][member_i])

        native = dims.get(measure_dim)
        if native not in measure_columns:
            continue

        entity_key = tuple(dims.get(dim) for dim in entity_dims)
        record = records.get(entity_key)
        if record is None:
            record = {"Category": category}
            for dim in entity_dims:
                record[ENTITY_DIM_COLUMN[dim]] = dims.get(dim)
            record["ReplicaID"] = 0
            # Entity categories with a time dimension are always sliced on the
            # ``LATEST`` bucket (see build_v11_entity_mdx), so the fallback is
            # accurate. ``by_rule`` has no time dimension at all — its cube is
            # cumulative since collection started — so ``TimeInterval`` there is
            # a constant placeholder for schema uniformity, NOT a snapshot
            # selector. Callers must not read a "now" semantic into it.
            record["TimeInterval"] = dims.get(time_dim, DEFAULT_TIME_INTERVAL) if time_dim else DEFAULT_TIME_INTERVAL
            # pre-create measure columns so column order/presence is stable
            for column in measure_columns.values():
                record[column] = None
            records[entity_key] = record

        record[measure_columns[native]] = cells[index].get("Value") if index < len(cells) else None

    return list(records.values())
