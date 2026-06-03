"""Module B — v11 MDX builder (pure).

Turns ``(category, cube, time_interval, include_control)`` into an MDX query
against the correct v11 ``}Stats*`` control cube. Layout convention (relied on
by the v11 record shaper):

- measures (the ``}StatsStats*`` dimension) always on axis 0 (columns);
- the entity dimension (e.g. ``}PerfCubes``) and/or the time dimension on
  axis 1 (rows), crossjoined when a full window is requested;
- a single time bucket (default ``LATEST``) goes in the ``WHERE`` slicer
  instead of an axis.

Dimension names below are verified against a live v11 server (11.8):
``}StatsByCube`` → dims ``[}StatsStatsByCube, }PerfCubes, }TimeIntervals]``;
``}StatsForServer`` → dims ``[}StatsStatsForServer, }TimeIntervals]``.
"""

from typing import Optional

from TM1py.Metrics.vocabulary import (
    CATEGORY_BY_CHORE,
    CATEGORY_BY_CLIENT,
    CATEGORY_BY_CUBE,
    CATEGORY_BY_CUBE_BY_CLIENT,
    CATEGORY_BY_PROCESS,
    CATEGORY_BY_RULE,
    CATEGORY_BY_SERVER,
    entity_measure_columns,
    v11_measure_names,
)

DEFAULT_TIME_INTERVAL = "LATEST"
# Sentinel for ``time_interval``: fetch the whole rolling window instead of one bucket.
ALL_TIME_INTERVALS = "ALL"
CUBES_TOTAL = "Cubes Total"

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


def _escape(name: str) -> str:
    """Escape ``]`` for an MDX bracketed name."""
    return name.replace("]", "]]")


def _measure_set(category: str, measure_dim: str) -> str:
    members = ",".join(f"[{measure_dim}].[{_escape(m)}]" for m in v11_measure_names(category))
    return "{" + members + "}"


def _entity_set(entity_dim: str, cube: Optional[str], include_control: bool) -> str:
    """Row set over the entity dimension, applying the v12-parity exclusions.

    An explicitly named ``cube`` is returned verbatim (even a control cube).
    Otherwise ``Cubes Total`` is always excluded; ``}``-control cubes are
    excluded unless ``include_control``.
    """
    if cube:
        return "{[" + entity_dim + "].[" + _escape(cube) + "]}"

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
    :param time_interval: ``None`` → ``LATEST`` snapshot (default);
        ``ALL`` → the full rolling window (time on an axis);
        any other string → that specific ``}TimeIntervals`` bucket.
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
        where = f" WHERE ([{time_dim}].[{_escape(bucket)}])"

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
    measures = ",".join(f"[{measure_dim}].[{_escape(m)}]" for m in entity_measure_columns(category))
    columns = "{" + measures + "}"

    cube_dim = spec["cube_dim"]
    entity_parts = []
    for dim in spec["entity_dims"]:
        if cube and dim == cube_dim:
            entity_parts.append("{[" + dim + "].[" + _escape(cube) + "]}")
        else:
            entity_parts.append("{TM1SUBSETALL([" + dim + "])}")
    rows = "NON EMPTY {" + " * ".join(entity_parts) + "}"

    where = ""
    if spec["time_dim"]:
        where = f" WHERE ([{spec['time_dim']}].[{DEFAULT_TIME_INTERVAL}])"

    return f"SELECT {columns} ON 0, {rows} ON 1 FROM [{spec['cube']}]{where}"
