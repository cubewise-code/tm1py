try:
    import pandas as pd

    _has_pandas = True
except ImportError:
    _has_pandas = False

import warnings
from typing import Dict, List

from TM1py.Exceptions.Exceptions import TM1pyVersionException
from TM1py.Metrics.mdx import build_v11_entity_mdx, build_v11_mdx
from TM1py.Metrics.odata_filter import build_metrics_url
from TM1py.Metrics.shapers import (
    shape_v11_entity_records,
    shape_v11_gauge_records,
    shape_v12_gauge_records,
)
from TM1py.Metrics.vocabulary import (
    CATEGORY_BY_CHORE,
    CATEGORY_BY_CLIENT,
    CATEGORY_BY_CUBE,
    CATEGORY_BY_CUBE_BY_CLIENT,
    CATEGORY_BY_PROCESS,
    CATEGORY_BY_RULE,
    CATEGORY_BY_SERVER,
)
from TM1py.Services.CellService import CellService
from TM1py.Services.CubeService import CubeService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import (
    format_url,
    require_pandas,
    require_version,
    verify_version,
)

V12_VERSION = "12.0.0"


class MetricService(ObjectService):
    """Expose TM1 model-performance statistics uniformly across v11 and v12.

    One method per Stats Category (``by_cube``, ``by_server``, ...). Each method
    returns the same shape regardless of the underlying TM1 version, hiding
    whether the data came from a v11 ``}Stats*`` control cube (MDX/cellset) or
    the v12 ``Metrics()`` OData endpoint. Reads never mutate server state.
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

        Always one row per replica with a ``ReplicaID`` column (v11 → ``0``).
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
