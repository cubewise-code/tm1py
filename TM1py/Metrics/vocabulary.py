"""Module A — metric vocabulary / normalizer (pure).

Maps a raw v11 native measure name to the canonical ``Metric`` name (IBM's v12
names, verbatim) plus its ``Unit``, per Stats Category. v12 records need no
remapping (``NativeName == Metric`` and the API carries the unit); this module
covers the v11 → canonical direction and is the single source of truth for the
mapping tables mirrored in ``CONTEXT.md``.

Decisions of record (see ``docs/adr/0002-metrics-canonical-names-and-units.md``):

- Canonical ``Metric`` = v12 names verbatim; v11-only measures get new canonical
  names following the same convention/prefix.
- All ``by_server`` metrics keep the ``replica_`` prefix; v11 is treated as a
  single replica (``ReplicaID=0``).
- Units pass through, never converted. v11 memory is raw **bytes** (``B``);
  counts are ``#``. A handful of v11 measures are genuinely unit-less (``None``).
"""

from typing import Dict, List, Optional, Tuple

from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict

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
    """Return the native-measure → column-name map for an entity category."""
    try:
        return dict(ENTITY_MEASURE_COLUMNS[category])
    except KeyError:
        raise KeyError(f"Unknown entity Stats Category: '{category}'")


# v11 native measure name -> (canonical Metric name, v11 Unit).
# Order matters: it is the order measures are requested in the v11 MDX and the
# order ``v11_measure_names`` returns. Overlapping (v12-shared) measures first,
# then v11-only measures, mirroring the CONTEXT.md tables top to bottom.
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
