"""Expose TM1 model-performance statistics uniformly across v11 and v12.

This module holds both the :class:`MetricService` (version dispatch + REST I/O)
and the pure, server-free helpers it delegates to: the v11 measure vocabulary,
the v11 MDX builders, the v12 ``Metrics()`` ``$filter`` builder, and the record
shapers. Keeping the helpers at module scope lets them be unit-tested without a
live TM1 server while the service stays a thin orchestrator.

One method per Stats Category (``by_cube``, ``by_server``, ...). Each method
returns the same shape regardless of the underlying TM1 version, hiding whether
the data came from a v11 ``}Stats*`` control cube (MDX/cellset) or the v12
``Metrics()`` OData endpoint. Reads never mutate server state. Two record
orientations:

- *gauge-long* (``by_cube``, ``by_server``): one row per metric, with
  ``Metric``/``Value``/``Unit``.
- *entity-wide* (``by_rule`` and the v11-only entity categories): one row per
  entity with heterogeneous attribute columns.

Values are passed through verbatim — never converted. Read ``Unit`` to interpret
them (v11 memory is raw bytes; v12 reports its own unit).
"""

try:
    import pandas as pd

    _has_pandas = True
except ImportError:
    _has_pandas = False

import itertools
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from TM1py.Exceptions.Exceptions import TM1pyVersionException
from TM1py.Services.CellService import CellService
from TM1py.Services.CubeService import CubeService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import (
    CaseAndSpaceInsensitiveDict,
    build_url_friendly_object_name,
    datetime_to_iso,
    format_url,
    require_pandas,
    require_version,
    verify_version,
)

V12_VERSION = "12.0.0"

CATEGORY_BY_CUBE = "by_cube"
CATEGORY_BY_SERVER = "by_server"

# Entity (wide) categories. ``by_rule`` is the only one present on both versions.
CATEGORY_BY_RULE = "by_rule"
CATEGORY_BY_PROCESS = "by_process"
CATEGORY_BY_CHORE = "by_chore"
CATEGORY_BY_CLIENT = "by_client"
CATEGORY_BY_CUBE_BY_CLIENT = "by_cube_by_client"

UNIT_BYTES = "B"
UNIT_COUNT = "#"

DEFAULT_TIME_INTERVAL = "LATEST"
# Sentinel for ``time_interval``: fetch the whole rolling window instead of one bucket.
ALL_TIME_INTERVALS = "ALL"
CUBES_TOTAL = "Cubes Total"


# --------------------------------------------------------------------------- #
# metric vocabulary / normalizer
#
# Maps a raw v11 native measure name to the canonical ``Metric`` name (IBM's v12
# names, verbatim) plus its ``Unit``, per Stats Category. v12 records need no
# remapping (``NativeName == Metric`` and the API carries the unit); these tables
# cover the v11 -> canonical direction. Canonical ``Metric`` = v12 names verbatim;
# v11-only measures get new canonical names following the same convention/prefix.
# All ``by_server`` metrics keep the ``replica_`` prefix; v11 is treated as a
# single replica (``ReplicaID=0``). Units pass through, never converted: v11
# memory is raw bytes (``B``), counts are ``#``, and a few v11 measures are
# genuinely unit-less (``None``).
# --------------------------------------------------------------------------- #

# Entity dimension -> the wide-record column name for that entity.
ENTITY_DIM_COLUMN = {
    "}Cubes": "CubeName",
    "}PerfCubes": "CubeName",
    "}LineNumber": "LineNumber",
    "}Processes": "ProcessName",
    "}Chores": "ChoreName",
    "}PerfClients": "ClientName",
    "}Cube Functions": "CubeFunction",
}

# Per entity category: v11 native measure name -> wide-record column name.
ENTITY_MEASURE_COLUMNS: Dict[str, Dict[str, str]] = {
    CATEGORY_BY_RULE: {
        "Rule Text": "RuleText",
        "Total Run Count": "TotalRunCount",
        "Min Time (ms)": "MinTimeMs",
        "Max Time (ms)": "MaxTimeMs",
        "Avg Time (ms)": "AvgTimeMs",
        "Total Time (ms)": "TotalTimeMs",
        "Last Run Time": "LastRunTime",
    },
    CATEGORY_BY_PROCESS: {
        "Current State": "CurrentState",
        "Completion Status": "CompletionStatus",
        "Client Name": "ClientName",
        "Last Start Time": "LastStartTime",
        "Last End Time": "LastEndTime",
        "Last Duration": "LastDuration",
        "Next Activation Time": "NextActivationTime",
        "Current Process": "CurrentProcess",
    },
    CATEGORY_BY_CLIENT: {
        "Message Count": "MessageCount",
        "Message Bytes": "MessageBytes",
        "Request Count": "RequestCount",
        "Elapse Time (ms)": "ElapseTimeMs",
        "Bytes/Message": "BytesPerMessage",
    },
    CATEGORY_BY_CUBE_BY_CLIENT: {
        "Count": "Count",
        "Elapse Time (ms)": "ElapseTimeMs",
    },
}
# }StatsByChore shares the }StatsByProcess measure dimension.
ENTITY_MEASURE_COLUMNS[CATEGORY_BY_CHORE] = dict(ENTITY_MEASURE_COLUMNS[CATEGORY_BY_PROCESS])


def entity_measure_columns(category: str) -> Dict[str, str]:
    """Return the native-measure -> column-name map for an entity category."""
    try:
        return dict(ENTITY_MEASURE_COLUMNS[category])
    except KeyError:
        raise KeyError(f"Unknown entity Stats Category: '{category}'")


# v11 native measure name -> (canonical Metric name, v11 Unit).
# Order matters: it is the order measures are requested in the v11 MDX and the
# order ``v11_measure_names`` returns. Overlapping (v12-shared) measures first,
# then v11-only measures.
_BY_CUBE: Dict[str, Tuple[str, Optional[str]]] = {
    "Total Memory Used": ("cube_memory_used", UNIT_BYTES),
    "Memory Used for Input Data": ("cube_memory_used_for_cell_values", UNIT_BYTES),
    "Memory Used for Feeders": ("cube_memory_used_for_feeder_flags", UNIT_BYTES),
    "Number of Fed Cells": ("cube_num_fed_cells", UNIT_COUNT),
    "Number of Populated Numeric Cells": ("cube_num_populated_numeric_cells", UNIT_COUNT),
    "Number of Populated String Cells": ("cube_num_populated_string_cells", UNIT_COUNT),
    # v11-only below
    "Memory Used for Views": ("cube_memory_used_for_views", UNIT_BYTES),
    "Number of Stored Views": ("cube_num_stored_views", UNIT_COUNT),
    "Number of Stored Calculated Cells": ("cube_num_stored_calculated_cells", UNIT_COUNT),
    "Memory Used for Calculations": ("cube_memory_used_for_calculations", UNIT_BYTES),
    "Rule calculation cache miss rate": ("cube_rule_calc_cache_miss_rate", None),
    "Steps of Average Calculation": ("cube_avg_calculation_steps", None),
}

_BY_SERVER: Dict[str, Tuple[str, Optional[str]]] = {
    "Memory Used": ("replica_memory_used", UNIT_BYTES),
    # v11-only below
    "Number of Connected Clients": ("replica_num_connected_clients", UNIT_COUNT),
    "Number of Active Threads": ("replica_num_active_threads", UNIT_COUNT),
    "Memory In Garbage": ("replica_memory_in_garbage", UNIT_BYTES),
}

# Per-category lookup. Built as case/space-insensitive so v11 measure names that
# vary in casing/spacing across server versions still resolve.
_TABLES: Dict[str, Dict[str, Tuple[str, Optional[str]]]] = {
    CATEGORY_BY_CUBE: _BY_CUBE,
    CATEGORY_BY_SERVER: _BY_SERVER,
}

_LOOKUPS: Dict[str, CaseAndSpaceInsensitiveDict] = {
    category: CaseAndSpaceInsensitiveDict(table) for category, table in _TABLES.items()
}


def normalize_v11_measure(category: str, native_name: str) -> Tuple[str, str, Optional[str]]:
    """Normalize a raw v11 measure into ``(Metric, NativeName, Unit)``.

    :param category: a gauge Stats Category (``by_cube`` / ``by_server``).
    :param native_name: the v11 measure name as reported by the ``}Stats*`` cube.
    :raises KeyError: if the category is not a known gauge category, or the
        measure is not in that category's mapping table.
    :return: ``(canonical Metric, native_name as supplied, Unit)``.
    """
    try:
        lookup = _LOOKUPS[category]
    except KeyError:
        raise KeyError(f"Unknown gauge Stats Category: '{category}'")

    metric, unit = lookup[native_name]
    return metric, native_name, unit


def v11_measure_names(category: str) -> List[str]:
    """Return the v11 native measure names for a gauge category, in canonical order.

    Used by the v11 MDX builder to select exactly the measures TM1py maps.
    """
    try:
        return list(_TABLES[category].keys())
    except KeyError:
        raise KeyError(f"Unknown gauge Stats Category: '{category}'")


# --------------------------------------------------------------------------- #
# v11 MDX builders
#
# Turn ``(category, cube, time_interval, include_control)`` into an MDX query
# against the correct v11 ``}Stats*`` control cube. Layout convention (relied on
# by the v11 record shapers):
#
# - measures (the ``}StatsStats*`` dimension) always on axis 0 (columns);
# - the entity dimension (e.g. ``}PerfCubes``) and/or the time dimension on
#   axis 1 (rows), crossjoined when a full window is requested;
# - a single time bucket (default ``LATEST``) goes in the ``WHERE`` slicer.
#
# Dimension names are verified against a live v11 server (11.8).
# --------------------------------------------------------------------------- #

# Per gauge category: the control cube and its measure / entity / time dimensions.
_SPEC = {
    CATEGORY_BY_CUBE: {
        "cube": "}StatsByCube",
        "measure_dim": "}StatsStatsByCube",
        "entity_dim": "}PerfCubes",
        "time_dim": "}TimeIntervals",
    },
    CATEGORY_BY_SERVER: {
        "cube": "}StatsForServer",
        "measure_dim": "}StatsStatsForServer",
        "entity_dim": None,
        "time_dim": "}TimeIntervals",
    },
}


# Per entity (wide) category: the control cube, its measure dimension, the
# entity dimension(s) that form the rows, an optional time dimension, and the
# entity dimension a ``cube`` filter applies to (if any).
# Dimension layouts verified against a live v11 server (11.8).
_ENTITY_SPEC = {
    CATEGORY_BY_RULE: {
        "cube": "}StatsByRule",
        "measure_dim": "}RuleStats",
        "entity_dims": ["}Cubes", "}LineNumber"],
        "time_dim": None,
        "cube_dim": "}Cubes",
    },
    CATEGORY_BY_PROCESS: {
        "cube": "}StatsByProcess",
        "measure_dim": "}StatsByProcess",
        "entity_dims": ["}Processes"],
        "time_dim": "}TimeIntervals",
        "cube_dim": None,
    },
    CATEGORY_BY_CHORE: {
        "cube": "}StatsByChore",
        "measure_dim": "}StatsByProcess",
        "entity_dims": ["}Chores"],
        "time_dim": "}TimeIntervals",
        "cube_dim": None,
    },
    CATEGORY_BY_CLIENT: {
        "cube": "}StatsByClient",
        "measure_dim": "}StatsStatsByClient",
        "entity_dims": ["}PerfClients"],
        "time_dim": "}TimeIntervals",
        "cube_dim": None,
    },
    CATEGORY_BY_CUBE_BY_CLIENT: {
        "cube": "}StatsByCubeByClient",
        "measure_dim": "}StatsStatsByCubeByClient",
        "entity_dims": ["}PerfCubes", "}PerfClients", "}Cube Functions"],
        "time_dim": "}TimeIntervals",
        "cube_dim": "}PerfCubes",
    },
}


def v11_spec(category: str) -> dict:
    """Return a copy of the v11 cube/dimension spec for a gauge category.

    Used by the record shaper to map cellset members to their dimension roles.

    :raises KeyError: if ``category`` is not a gauge category.
    """
    try:
        return dict(_SPEC[category])
    except KeyError:
        raise KeyError(f"Unknown gauge Stats Category: '{category}'")


def v11_entity_spec(category: str) -> dict:
    """Return a copy of the v11 cube/dimension spec for an entity category.

    :raises KeyError: if ``category`` is not an entity category.
    """
    try:
        return dict(_ENTITY_SPEC[category])
    except KeyError:
        raise KeyError(f"Unknown entity Stats Category: '{category}'")


def _escape_mdx(name: str) -> str:
    """Escape ``]`` for an MDX bracketed name."""
    return name.replace("]", "]]")


def _measure_set(category: str, measure_dim: str) -> str:
    members = ",".join(f"[{measure_dim}].[{_escape_mdx(m)}]" for m in v11_measure_names(category))
    return "{" + members + "}"


def _entity_set(entity_dim: str, cube: Optional[str], include_control: bool) -> str:
    """Row set over the entity dimension, applying the v12-parity exclusions.

    An explicitly named ``cube`` is returned verbatim (even a control cube).
    Otherwise ``Cubes Total`` is always excluded; ``}``-control cubes are
    excluded unless ``include_control``.
    """
    if cube:
        return "{[" + entity_dim + "].[" + _escape_mdx(cube) + "]}"

    all_members = "{TM1SUBSETALL([" + entity_dim + "])}"
    excluded = "[" + entity_dim + "].[" + CUBES_TOTAL + "]"
    if not include_control:
        excluded = "TM1FILTERBYPATTERN(" + all_members + ',"}*"),' + excluded
    return "{EXCEPT(" + all_members + ",{" + excluded + "})}"


def build_v11_mdx(
    category: str,
    cube: str = None,
    time_interval: str = None,
    include_control: bool = False,
) -> str:
    """Build the v11 MDX for a gauge category.

    :param category: ``by_cube`` or ``by_server``.
    :param cube: restrict to a single entity (``by_cube`` only); ignored where
        the category has no entity dimension.
    :param time_interval: ``None`` -> ``LATEST`` snapshot (default);
        ``ALL`` -> the full rolling window (time on an axis);
        any other string -> that specific ``}TimeIntervals`` bucket.
    :param include_control: include ``}``-control cubes (``by_cube`` only).
    :raises KeyError: if ``category`` is not a gauge category.
    """
    try:
        spec = _SPEC[category]
    except KeyError:
        raise KeyError(f"Unknown gauge Stats Category: '{category}'")

    columns = _measure_set(category, spec["measure_dim"])
    time_dim = spec["time_dim"]
    entity_dim = spec["entity_dim"]
    full_window = time_interval == ALL_TIME_INTERVALS

    # Build the rows axis (entity and/or time) and the optional WHERE slicer.
    row_parts = []
    if entity_dim:
        row_parts.append(_entity_set(entity_dim, cube, include_control))
    if full_window:
        row_parts.append("{[" + time_dim + "].Members}")

    where = ""
    if not full_window:
        bucket = time_interval or DEFAULT_TIME_INTERVAL
        where = f" WHERE ([{time_dim}].[{_escape_mdx(bucket)}])"

    rows = " * ".join(row_parts)
    axes = columns + " ON 0"
    if rows:
        axes += ", " + rows + " ON 1"

    return f"SELECT {axes} FROM [{spec['cube']}]{where}"


def build_v11_entity_mdx(category: str, cube: str = None) -> str:
    """Build the v11 MDX for an entity (wide) category.

    Measures (the category's measure dimension) go on axis 0; the entity
    dimension(s) are crossjoined ``NON EMPTY`` on axis 1; a ``LATEST`` slicer is
    added when the cube has a time dimension. ``cube`` restricts the relevant
    entity dimension to a single member.

    :raises KeyError: if ``category`` is not an entity category.
    """
    try:
        spec = _ENTITY_SPEC[category]
    except KeyError:
        raise KeyError(f"Unknown entity Stats Category: '{category}'")

    measure_dim = spec["measure_dim"]
    measures = ",".join(f"[{measure_dim}].[{_escape_mdx(m)}]" for m in entity_measure_columns(category))
    columns = "{" + measures + "}"

    cube_dim = spec["cube_dim"]
    entity_parts = []
    for dim in spec["entity_dims"]:
        if cube and dim == cube_dim:
            entity_parts.append("{[" + dim + "].[" + _escape_mdx(cube) + "]}")
        else:
            entity_parts.append("{TM1SUBSETALL([" + dim + "])}")
    rows = "NON EMPTY {" + " * ".join(entity_parts) + "}"

    where = ""
    if spec["time_dim"]:
        where = f" WHERE ([{spec['time_dim']}].[{DEFAULT_TIME_INTERVAL}])"

    return f"SELECT {columns} ON 0, {rows} ON 1 FROM [{spec['cube']}]{where}"


# --------------------------------------------------------------------------- #
# v12 Metrics() $filter builder
# --------------------------------------------------------------------------- #


def build_metrics_url(
    cube_name: str = None,
    metrics: Optional[List[str]] = None,
    timestamp: datetime = None,
) -> str:
    """Build the relative ``/Metrics()`` URL, optionally with a ``$filter``.

    :param cube_name: restrict to a single cube (``CubeName eq '<cube>'``).
    :param metrics: restrict to these canonical metric names
        (``Name eq 'm1' or Name eq 'm2' ...``).
    :param timestamp: only metrics newer than this (``Timestamp gt <iso>``).
    :return: ``"/Metrics()"`` or ``"/Metrics()?$filter=..."``.
    """
    clauses: List[str] = []

    if cube_name:
        clauses.append(f"CubeName eq '{build_url_friendly_object_name(cube_name)}'")

    if metrics:
        clauses.append(" or ".join(f"Name eq '{build_url_friendly_object_name(m)}'" for m in metrics))

    if timestamp:
        clauses.append(f"Timestamp gt {datetime_to_iso(timestamp)}")

    if not clauses:
        return "/Metrics()"

    filter_string = " and ".join(f"({clause})" for clause in clauses)
    return f"/Metrics()?$filter={filter_string}"


# --------------------------------------------------------------------------- #
# record shapers
#
# Turn raw payloads (v12 ``Metrics()`` JSON ``value`` list; v11 cellset) into the
# unified record dicts the service returns. Values are passed through verbatim —
# never converted.
# --------------------------------------------------------------------------- #

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


def _axis_tuples_by_dimension(axes: List[Dict]) -> List[List[Dict[str, str]]]:
    """Pre-resolve each tuple on each axis into ``{dimension: member_name}``."""
    return [[{_dimension_of(m): m["Name"] for m in tup["Members"]} for tup in axis["Tuples"]] for axis in axes]


def _cell_index(coord: Tuple[int, ...], sizes: List[int]) -> int:
    """OData cell ordinal for an axis coordinate (axis 0 varies fastest)."""
    index = 0
    factor = 1
    for axis_i, member_i in enumerate(coord):
        index += member_i * factor
        factor *= sizes[axis_i]
    return index


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

    axis_tuples = _axis_tuples_by_dimension(axes)
    cells = cellset.get("Cells", [])

    records: List[Dict] = []
    for coord in itertools.product(*(range(size) for size in sizes)):
        index = _cell_index(coord, sizes)

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
        index = _cell_index(coord, sizes)

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


class MetricService(ObjectService):
    """Expose TM1 model-performance statistics uniformly across v11 and v12.

    One method per Stats Category (``by_cube``, ``by_server``, ...). Each method
    returns the same shape regardless of the underlying TM1 version, hiding
    whether the data came from a v11 ``}Stats*`` control cube (MDX/cellset) or
    the v12 ``Metrics()`` OData endpoint. Reads never mutate server state.

    Two return orientations, chosen by the data's nature:

    - *gauge-long* (``by_cube``, ``by_server``): one row per metric, with
      ``Metric`` / ``Value`` / ``Unit``.
    - *entity-wide* (``by_rule`` and the v11-only categories): one row per
      entity with attribute columns.

    Every read method has a parallel ``*_as_dataframe`` variant.

    Per-cube metrics (gauge-long), unified across versions::

        >>> rows = tm1.metrics.by_cube(cube="plan_BudgetPlan")
        >>> rows[0]
        {'Category': 'by_cube', 'CubeName': 'plan_BudgetPlan',
         'Metric': 'cube_memory_used', 'NativeName': 'Total Memory Used',
         'Value': 8385536, 'Unit': 'B', 'ReplicaID': 0,
         'TimeInterval': 'LATEST', 'Timestamp': None}

    The canonical ``Metric`` name is stable across versions; ``NativeName``
    carries the source's own name. Values pass through unconverted — read
    ``Unit`` to interpret them (``cube_memory_used`` is bytes on v11, KB on v12).
    As a filtered DataFrame::

        >>> df = tm1.metrics.by_cube_as_dataframe(metrics=["cube_memory_used"])

    Server/replica-level metrics. v12 (highly-available) yields one row per
    replica; v11 is a single replica (``ReplicaID=0``)::

        >>> tm1.metrics.by_server(metrics=["replica_memory_used"])

    Per-rule timing. On v12 rule stats are collected on demand; on v11 the
    Performance Monitor populates ``}StatsByRule``. The read is identical::

        >>> tm1.metrics.start_collecting_rule_stats("plan_BudgetPlan")  # v12 only
        >>> tm1.metrics.flush_collected_rule_stats("plan_BudgetPlan")   # writes }StatsByRule
        >>> tm1.metrics.stop_collecting_rule_stats("plan_BudgetPlan")
        >>> tm1.metrics.by_rule(cube="plan_BudgetPlan")

    v11-only categories (the cubes were removed in v12; these raise
    :class:`TM1pyVersionException` on a v12 database)::

        >>> tm1.metrics.by_process()
        >>> tm1.metrics.by_chore()
        >>> tm1.metrics.by_client()
        >>> tm1.metrics.by_cube_by_client(cube="plan_BudgetPlan")
    """

    STATS_BY_RULE_CUBE = "}StatsByRule"

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self._cells = None
        self._cubes = None

    @property
    def _cell_service(self) -> CellService:
        if self._cells is None:
            self._cells = CellService(self._rest)
        return self._cells

    @property
    def _cube_service(self) -> CubeService:
        if self._cubes is None:
            self._cubes = CubeService(self._rest)
        return self._cubes

    @property
    def _is_v12(self) -> bool:
        return verify_version(required_version=V12_VERSION, version=self.version)

    # ------------------------------------------------------------------ #
    # gauge categories
    # ------------------------------------------------------------------ #

    def by_cube(
        self,
        cube: str = None,
        metrics: List[str] = None,
        time_interval: str = None,
        include_control: bool = False,
        **kwargs,
    ) -> List[Dict]:
        """Per-cube performance metrics (gauge-long), unified across versions.

        ``}``-control cubes and the synthetic ``Cubes Total`` row are excluded
        by default; ``include_control=True`` adds ``}``-cubes (v11 only).
        """
        if self._is_v12:
            self._reject_time_interval(time_interval, "by_cube")
            if include_control:
                warnings.warn(
                    "include_control has no effect on v12: Metrics() never reports '}'-control cubes.",
                    stacklevel=2,
                )
            return self._gauge_v12(CATEGORY_BY_CUBE, cube=cube, metrics=metrics, **kwargs)
        return self._gauge_v11(
            CATEGORY_BY_CUBE,
            cube=cube,
            metrics=metrics,
            time_interval=time_interval,
            include_control=include_control,
            **kwargs,
        )

    @require_pandas
    def by_cube_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_cube(*args, **kwargs))

    def by_server(self, metrics: List[str] = None, time_interval: str = None, **kwargs) -> List[Dict]:
        """Server/replica-level metrics (gauge-long), unified across versions.

        Always one row per replica with a ``ReplicaID`` column (v11 -> ``0``).
        """
        if self._is_v12:
            self._reject_time_interval(time_interval, "by_server")
            return self._gauge_v12(CATEGORY_BY_SERVER, cube=None, metrics=metrics, **kwargs)
        return self._gauge_v11(CATEGORY_BY_SERVER, cube=None, metrics=metrics, time_interval=time_interval, **kwargs)

    @require_pandas
    def by_server_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_server(*args, **kwargs))

    # ------------------------------------------------------------------ #
    # entity categories
    # ------------------------------------------------------------------ #

    def by_rule(self, cube: str = None, **kwargs) -> List[Dict]:
        """Per-rule-line statistics (entity-wide), unified across versions.

        ``}StatsByRule`` is structurally identical on v11 and v12, so the same
        cellset read/shape path serves both. On v12 the cube only exists once
        :meth:`flush_collected_rule_stats` has created it; if it is absent this
        returns ``[]`` with a warning rather than raising.
        """
        if not self._cube_service.exists(self.STATS_BY_RULE_CUBE, **kwargs):
            if self._is_v12:
                hint = (
                    "rule stats have not been collected/flushed — call start_collecting_rule_stats(cube) "
                    "then flush_collected_rule_stats(cube)"
                )
            else:
                hint = (
                    "rule stats have not been collected — ensure Performance Monitor is running "
                    "(ServerService.start_performance_monitor)"
                )
            warnings.warn(
                f"'{self.STATS_BY_RULE_CUBE}' does not exist; {hint}. Returning no records.",
                stacklevel=2,
            )
            return []
        return self._entity_v11(CATEGORY_BY_RULE, cube=cube, **kwargs)

    @require_pandas
    def by_rule_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_rule(*args, **kwargs))

    def by_process(self, **kwargs) -> List[Dict]:
        """Per-process execution statistics (entity-wide). v11 only."""
        self._require_v11(CATEGORY_BY_PROCESS)
        return self._entity_v11(CATEGORY_BY_PROCESS, **kwargs)

    @require_pandas
    def by_process_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_process(*args, **kwargs))

    def by_chore(self, **kwargs) -> List[Dict]:
        """Per-chore execution statistics (entity-wide). v11 only."""
        self._require_v11(CATEGORY_BY_CHORE)
        return self._entity_v11(CATEGORY_BY_CHORE, **kwargs)

    @require_pandas
    def by_chore_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_chore(*args, **kwargs))

    def by_client(self, **kwargs) -> List[Dict]:
        """Per-client request/message statistics (entity-wide). v11 only."""
        self._require_v11(CATEGORY_BY_CLIENT)
        return self._entity_v11(CATEGORY_BY_CLIENT, **kwargs)

    @require_pandas
    def by_client_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_client(*args, **kwargs))

    def by_cube_by_client(self, cube: str = None, **kwargs) -> List[Dict]:
        """Per-cube-per-client access statistics (entity-wide). v11 only."""
        self._require_v11(CATEGORY_BY_CUBE_BY_CLIENT)
        return self._entity_v11(CATEGORY_BY_CUBE_BY_CLIENT, cube=cube, **kwargs)

    @require_pandas
    def by_cube_by_client_as_dataframe(self, *args, **kwargs) -> "pd.DataFrame":
        return pd.DataFrame.from_records(self.by_cube_by_client(*args, **kwargs))

    # ------------------------------------------------------------------ #
    # v12 rule-stats collection lifecycle (cube-bound actions)
    # ------------------------------------------------------------------ #

    @require_version(version=V12_VERSION)
    def start_collecting_rule_stats(self, cube: str, **kwargs):
        """Start collecting per-rule timing statistics for ``cube`` (v12)."""
        return self._rule_stats_action(cube, "StartCollectingRuleStats", **kwargs)

    @require_version(version=V12_VERSION)
    def stop_collecting_rule_stats(self, cube: str, **kwargs):
        """Stop collecting per-rule timing statistics for ``cube`` (v12)."""
        return self._rule_stats_action(cube, "StopCollectingRuleStats", **kwargs)

    @require_version(version=V12_VERSION)
    def flush_collected_rule_stats(self, cube: str, **kwargs):
        """Flush collected rule stats into ``}StatsByRule`` for ``cube`` (v12).

        Creates the ``}StatsByRule`` cube on demand if it does not yet exist.
        """
        return self._rule_stats_action(cube, "FlushCollectedRuleStats", **kwargs)

    def _rule_stats_action(self, cube: str, action: str, **kwargs):
        url = format_url("/Cubes('{}')/tm1." + action, cube)
        return self._rest.POST(url, **kwargs)

    # ------------------------------------------------------------------ #
    # version-specific readers
    # ------------------------------------------------------------------ #

    def _gauge_v12(self, category: str, cube: str = None, metrics: List[str] = None, **kwargs) -> List[Dict]:
        url = build_metrics_url(cube_name=cube, metrics=metrics)
        raw = self._rest.GET(url, **kwargs).json().get("value", [])
        return shape_v12_gauge_records(raw, category)

    def _gauge_v11(
        self,
        category: str,
        cube: str = None,
        metrics: List[str] = None,
        time_interval: str = None,
        include_control: bool = False,
        **kwargs,
    ) -> List[Dict]:
        mdx = build_v11_mdx(category, cube=cube, time_interval=time_interval, include_control=include_control)
        raw = self._read_cellset(mdx, **kwargs)
        records = shape_v11_gauge_records(raw, category)
        if metrics:
            wanted = set(metrics)
            records = [record for record in records if record["Metric"] in wanted]
        return records

    def _entity_v11(self, category: str, cube: str = None, **kwargs) -> List[Dict]:
        mdx = build_v11_entity_mdx(category, cube=cube)
        raw = self._read_cellset(mdx, **kwargs)
        return shape_v11_entity_records(raw, category)

    def _read_cellset(self, mdx: str, **kwargs) -> Dict:
        """Create a cellset, extract the raw (Name + UniqueName) payload, tidy up."""
        cellset_id = self._cell_service.create_cellset(mdx=mdx, **kwargs)
        try:
            return self._cell_service.extract_cellset_raw_response(
                cellset_id, member_properties=["Name", "UniqueName"], **kwargs
            ).json()
        finally:
            self._cell_service.delete_cellset(cellset_id, **kwargs)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _require_v11(self, function: str) -> None:
        """v11-only categories have no v12 source; raise a clear version error."""
        if self._is_v12:
            raise TM1pyVersionException(
                function=function,
                required_version=V12_VERSION,
                max_version=V12_VERSION,
                feature=f"'{function}' is a v11-only Stats Category (no v12 source exists)",
            )

    @staticmethod
    def _reject_time_interval(time_interval, function: str) -> None:
        """``time_interval`` is a v11-only rolling-window concept; reject it on v12."""
        if time_interval is not None:
            raise TM1pyVersionException(
                function=f"{function}(time_interval=...)",
                required_version=V12_VERSION,
                max_version=V12_VERSION,
                feature="time_interval (v11 rolling window) is not available on v12",
            )
