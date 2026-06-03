"""Tests for MetricService.

Two layers in one file (matching TM1py's one-test-file-per-service convention):

- Server-free unit tests for the pure helpers (vocabulary, v11 MDX builders,
  v12 ``Metrics()`` ``$filter`` builder, record shapers). The v11 shaper tests
  are driven by fixtures captured once from live servers under
  ``Tests/resources/metrics/`` plus small hand-built payloads.
- Integration tests for the service itself, run against the live servers in
  ``config.ini``. Connections are classified by version at setup, so the same
  suite asserts the unified schema on both a v11 and a v12 server; each test
  skips cleanly when the relevant server is absent.
"""

import configparser
import json
import unittest
from datetime import datetime
from pathlib import Path

from TM1py import TM1Service
from TM1py.Exceptions.Exceptions import TM1pyVersionException
from TM1py.Services.MetricService import (
    ALL_TIME_INTERVALS,
    CATEGORY_BY_CUBE,
    CATEGORY_BY_SERVER,
    UNIT_BYTES,
    UNIT_COUNT,
    build_metrics_url,
    build_v11_mdx,
    normalize_v11_measure,
    shape_v11_entity_records,
    shape_v11_gauge_records,
    shape_v12_gauge_records,
    v11_measure_names,
)
from TM1py.Utils.Utils import verify_version

CONFIG = Path(__file__).parent / "config.ini"
FIXTURES = Path(__file__).parent / "resources" / "metrics"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def _member(dim, name):
    return {"Name": name, "UniqueName": f"[{dim}].[{dim}].[{name}]"}


def _axis(ordinal, tuples_members):
    return {"Ordinal": ordinal, "Tuples": [{"Members": members} for members in tuples_members]}


# ====================================================================== #
# unit tests — metric vocabulary / normalizer
# ====================================================================== #


class TestMetricVocabulary(unittest.TestCase):
    def test_by_cube_overlapping_measures_map_to_v12_names(self):
        cases = {
            "Total Memory Used": ("cube_memory_used", UNIT_BYTES),
            "Memory Used for Input Data": ("cube_memory_used_for_cell_values", UNIT_BYTES),
            "Memory Used for Feeders": ("cube_memory_used_for_feeder_flags", UNIT_BYTES),
            "Number of Fed Cells": ("cube_num_fed_cells", UNIT_COUNT),
            "Number of Populated Numeric Cells": ("cube_num_populated_numeric_cells", UNIT_COUNT),
            "Number of Populated String Cells": ("cube_num_populated_string_cells", UNIT_COUNT),
        }
        for native, (metric, unit) in cases.items():
            with self.subTest(native=native):
                result = normalize_v11_measure(CATEGORY_BY_CUBE, native)
                self.assertEqual(result, (metric, native, unit))

    def test_by_cube_v11_only_measures(self):
        cases = {
            "Memory Used for Views": ("cube_memory_used_for_views", UNIT_BYTES),
            "Number of Stored Views": ("cube_num_stored_views", UNIT_COUNT),
            "Number of Stored Calculated Cells": ("cube_num_stored_calculated_cells", UNIT_COUNT),
            "Memory Used for Calculations": ("cube_memory_used_for_calculations", UNIT_BYTES),
            "Rule calculation cache miss rate": ("cube_rule_calc_cache_miss_rate", None),
            "Steps of Average Calculation": ("cube_avg_calculation_steps", None),
        }
        for native, (metric, unit) in cases.items():
            with self.subTest(native=native):
                self.assertEqual(normalize_v11_measure(CATEGORY_BY_CUBE, native), (metric, native, unit))

    def test_by_server_keeps_replica_prefix(self):
        cases = {
            "Memory Used": ("replica_memory_used", UNIT_BYTES),
            "Number of Connected Clients": ("replica_num_connected_clients", UNIT_COUNT),
            "Number of Active Threads": ("replica_num_active_threads", UNIT_COUNT),
            "Memory In Garbage": ("replica_memory_in_garbage", UNIT_BYTES),
        }
        for native, (metric, unit) in cases.items():
            with self.subTest(native=native):
                metric_name, native_name, unit_ = normalize_v11_measure(CATEGORY_BY_SERVER, native)
                self.assertTrue(metric_name.startswith("replica_"))
                self.assertEqual((metric_name, native_name, unit_), (metric, native, unit))

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(
            normalize_v11_measure(CATEGORY_BY_CUBE, "totalmemoryused"),
            ("cube_memory_used", "totalmemoryused", UNIT_BYTES),
        )

    def test_unknown_measure_raises(self):
        with self.assertRaises(KeyError):
            normalize_v11_measure(CATEGORY_BY_CUBE, "Some Future Measure")

    def test_unknown_category_raises(self):
        with self.assertRaises(KeyError):
            normalize_v11_measure("by_unicorn", "Total Memory Used")

    def test_v11_measure_names_returns_native_names_for_mdx_selection(self):
        names = v11_measure_names(CATEGORY_BY_CUBE)
        self.assertIn("Total Memory Used", names)
        self.assertIn("Memory Used for Views", names)
        # canonical order: the overlapping v12 measures come first
        self.assertEqual(names[0], "Total Memory Used")

    def test_v11_measure_names_for_server(self):
        names = v11_measure_names(CATEGORY_BY_SERVER)
        self.assertIn("Memory Used", names)
        self.assertIn("Number of Connected Clients", names)


# ====================================================================== #
# unit tests — v11 MDX builder
# ====================================================================== #


BY_CUBE_MEASURES = (
    "{[}StatsStatsByCube].[Total Memory Used],"
    "[}StatsStatsByCube].[Memory Used for Input Data],"
    "[}StatsStatsByCube].[Memory Used for Feeders],"
    "[}StatsStatsByCube].[Number of Fed Cells],"
    "[}StatsStatsByCube].[Number of Populated Numeric Cells],"
    "[}StatsStatsByCube].[Number of Populated String Cells],"
    "[}StatsStatsByCube].[Memory Used for Views],"
    "[}StatsStatsByCube].[Number of Stored Views],"
    "[}StatsStatsByCube].[Number of Stored Calculated Cells],"
    "[}StatsStatsByCube].[Memory Used for Calculations],"
    "[}StatsStatsByCube].[Rule calculation cache miss rate],"
    "[}StatsStatsByCube].[Steps of Average Calculation]}"
)


class TestV11MdxBuilder(unittest.TestCase):
    def test_by_cube_latest_default_excludes_control_and_total(self):
        mdx = build_v11_mdx("by_cube")
        self.assertEqual(
            mdx,
            f"SELECT {BY_CUBE_MEASURES} ON 0, "
            "{EXCEPT({TM1SUBSETALL([}PerfCubes])},"
            '{TM1FILTERBYPATTERN({TM1SUBSETALL([}PerfCubes])},"}*"),[}PerfCubes].[Cubes Total]})} ON 1 '
            "FROM [}StatsByCube] WHERE ([}TimeIntervals].[LATEST])",
        )

    def test_by_cube_include_control_keeps_control_drops_only_total(self):
        mdx = build_v11_mdx("by_cube", include_control=True)
        self.assertIn(
            "{EXCEPT({TM1SUBSETALL([}PerfCubes])},{[}PerfCubes].[Cubes Total]})} ON 1",
            mdx,
        )
        self.assertNotIn("TM1FILTERBYPATTERN", mdx)

    def test_by_cube_single_cube_filter(self):
        mdx = build_v11_mdx("by_cube", cube="Sales")
        self.assertIn("{[}PerfCubes].[Sales]} ON 1", mdx)
        self.assertNotIn("TM1SUBSETALL", mdx)
        self.assertTrue(mdx.endswith("WHERE ([}TimeIntervals].[LATEST])"))

    def test_by_cube_specific_time_bucket_goes_in_where(self):
        mdx = build_v11_mdx("by_cube", cube="Sales", time_interval="0M05")
        self.assertTrue(mdx.endswith("WHERE ([}TimeIntervals].[0M05])"))

    def test_by_cube_full_window_puts_time_on_axis(self):
        mdx = build_v11_mdx("by_cube", cube="Sales", time_interval=ALL_TIME_INTERVALS)
        self.assertIn("{[}PerfCubes].[Sales]} * {[}TimeIntervals].Members} ON 1", mdx)
        self.assertNotIn("WHERE", mdx)

    def test_by_server_single_axis_latest(self):
        mdx = build_v11_mdx("by_server")
        self.assertEqual(
            mdx,
            "SELECT {[}StatsStatsForServer].[Memory Used],"
            "[}StatsStatsForServer].[Number of Connected Clients],"
            "[}StatsStatsForServer].[Number of Active Threads],"
            "[}StatsStatsForServer].[Memory In Garbage]} ON 0 "
            "FROM [}StatsForServer] WHERE ([}TimeIntervals].[LATEST])",
        )

    def test_by_server_ignores_cube_and_include_control(self):
        # by_server has no entity dimension; cube/include_control are no-ops
        self.assertEqual(build_v11_mdx("by_server", cube="Sales", include_control=True), build_v11_mdx("by_server"))

    def test_by_server_full_window_puts_time_on_axis(self):
        mdx = build_v11_mdx("by_server", time_interval=ALL_TIME_INTERVALS)
        self.assertIn("{[}TimeIntervals].Members} ON 1", mdx)
        self.assertNotIn("WHERE", mdx)

    def test_unknown_category_raises(self):
        with self.assertRaises(KeyError):
            build_v11_mdx("by_unicorn")


# ====================================================================== #
# unit tests — v12 Metrics() $filter builder
# ====================================================================== #


class TestMetricODataFilter(unittest.TestCase):
    def test_no_params_returns_bare_metrics_function(self):
        self.assertEqual(build_metrics_url(), "/Metrics()")

    def test_cube_filter(self):
        self.assertEqual(
            build_metrics_url(cube_name="Sales"),
            "/Metrics()?$filter=(CubeName eq 'Sales')",
        )

    def test_single_metric_filter(self):
        self.assertEqual(
            build_metrics_url(metrics=["cube_memory_used"]),
            "/Metrics()?$filter=(Name eq 'cube_memory_used')",
        )

    def test_multiple_metrics_are_or_joined_in_one_group(self):
        self.assertEqual(
            build_metrics_url(metrics=["cube_memory_used", "cube_num_fed_cells"]),
            "/Metrics()?$filter=(Name eq 'cube_memory_used' or Name eq 'cube_num_fed_cells')",
        )

    def test_timestamp_filter_is_unquoted_iso(self):
        ts = datetime(2026, 5, 8, 0, 2, 24)
        self.assertEqual(
            build_metrics_url(timestamp=ts),
            "/Metrics()?$filter=(Timestamp gt 2026-05-08T00:02:24.000Z)",
        )

    def test_all_params_combined_with_and(self):
        ts = datetime(2026, 5, 8, 0, 2, 24)
        self.assertEqual(
            build_metrics_url(cube_name="Sales", metrics=["cube_memory_used", "cube_num_fed_cells"], timestamp=ts),
            "/Metrics()?$filter=(CubeName eq 'Sales') and "
            "(Name eq 'cube_memory_used' or Name eq 'cube_num_fed_cells') and "
            "(Timestamp gt 2026-05-08T00:02:24.000Z)",
        )

    def test_single_quotes_in_cube_name_are_escaped(self):
        self.assertEqual(
            build_metrics_url(cube_name="Bob's Cube"),
            "/Metrics()?$filter=(CubeName eq 'Bob''s Cube')",
        )


# ====================================================================== #
# unit tests — v12 gauge record shaper
# ====================================================================== #


class TestV12GaugeShaper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _load("v12_metrics_raw.json")

    def test_by_cube_selects_only_cube_metrics(self):
        records = shape_v12_gauge_records(self.raw, category="by_cube")
        self.assertTrue(records)
        self.assertEqual(len(records), sum(1 for r in self.raw if r["Name"].startswith("cube_")))
        for rec in records:
            self.assertEqual(rec["Category"], "by_cube")
            self.assertTrue(rec["Metric"].startswith("cube_"))
            self.assertIsNotNone(rec["CubeName"])

    def test_by_server_selects_only_replica_metrics_without_cubename(self):
        records = shape_v12_gauge_records(self.raw, category="by_server")
        self.assertEqual(len(records), sum(1 for r in self.raw if r["Name"].startswith("replica_")))
        for rec in records:
            self.assertEqual(rec["Category"], "by_server")
            self.assertTrue(rec["Metric"].startswith("replica_"))
            self.assertNotIn("CubeName", rec)

    def test_common_and_gauge_columns_present(self):
        records = shape_v12_gauge_records(self.raw, category="by_cube")
        rec = records[0]
        for key in (
            "Category",
            "ReplicaID",
            "TimeInterval",
            "DatabaseName",
            "DatabaseID",
            "Metric",
            "NativeName",
            "Value",
            "Unit",
            "Timestamp",
            "CubeName",
        ):
            self.assertIn(key, rec)

    def test_timeinterval_defaults_to_latest(self):
        records = shape_v12_gauge_records(self.raw, category="by_server")
        self.assertTrue(all(r["TimeInterval"] == "LATEST" for r in records))

    def test_native_name_equals_metric_on_v12(self):
        records = shape_v12_gauge_records(self.raw, category="by_cube")
        self.assertTrue(all(r["NativeName"] == r["Metric"] for r in records))

    def test_replica_rows_with_null_cubename_excluded_from_by_cube(self):
        # replica_* rows carry CubeName=null; selection is by name prefix, so
        # they must never leak into by_cube regardless of CubeName.
        raw = [
            {"Name": "replica_memory_used", "Value": 1, "Unit": "KB", "CubeName": None},
            {"Name": "cube_memory_used", "Value": 2, "Unit": "KB", "CubeName": "Sales"},
        ]
        records = shape_v12_gauge_records(raw, category="by_cube")
        self.assertEqual([r["Metric"] for r in records], ["cube_memory_used"])
        self.assertEqual(records[0]["CubeName"], "Sales")

    def test_cube_row_with_null_cubename_passes_cubename_through_as_none(self):
        # a cube_* row whose CubeName is null is still selected (prefix match);
        # CubeName passes through as None rather than being dropped.
        raw = [{"Name": "cube_memory_used", "Value": 2, "Unit": "KB", "CubeName": None}]
        records = shape_v12_gauge_records(raw, category="by_cube")
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["CubeName"])

    def test_exact_record_shape_for_handbuilt_row(self):
        raw = [
            {
                "Name": "cube_memory_used",
                "Value": 36,
                "Unit": "KB",
                "Timestamp": "2026-05-08T00:02:24.000Z",
                "ReplicaID": 0,
                "DatabaseID": "db-123",
                "DatabaseName": "cw-v12-test",
                "CubeName": "Sales",
            }
        ]
        self.assertEqual(
            shape_v12_gauge_records(raw, category="by_cube"),
            [
                {
                    "Category": "by_cube",
                    "CubeName": "Sales",
                    "Metric": "cube_memory_used",
                    "NativeName": "cube_memory_used",
                    "Value": 36,
                    "Unit": "KB",
                    "ReplicaID": 0,
                    "TimeInterval": "LATEST",
                    "Timestamp": "2026-05-08T00:02:24.000Z",
                    "DatabaseName": "cw-v12-test",
                    "DatabaseID": "db-123",
                }
            ],
        )

    def test_value_is_never_converted(self):
        raw = [{"Name": "replica_memory_used", "Value": 123456, "Unit": "KB", "CubeName": None, "ReplicaID": 1}]
        rec = shape_v12_gauge_records(raw, category="by_server")[0]
        self.assertEqual(rec["Value"], 123456)
        self.assertEqual(rec["ReplicaID"], 1)


# ====================================================================== #
# unit tests — v11 gauge record shaper
# ====================================================================== #


class TestV11GaugeShaper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_cube = _load("v11_by_cube_cellset_raw.json")
        cls.by_server = _load("v11_by_server_cellset_raw.json")

    def test_by_cube_one_row_per_measure_per_cube(self):
        records = shape_v11_gauge_records(self.by_cube, category="by_cube")
        # fixture: 12 measures x 7 (non-control, no Cubes Total) cubes
        self.assertEqual(len(records), 84)
        cubes = {r["CubeName"] for r in records}
        self.assertEqual(len(cubes), 7)
        self.assertFalse(any(c.startswith("}") for c in cubes))
        self.assertNotIn("Cubes Total", cubes)

    def test_by_cube_record_is_normalized_gauge_long(self):
        records = shape_v11_gauge_records(self.by_cube, category="by_cube")
        rec = next(r for r in records if r["CubeName"] == "plan_BudgetPlan" and r["Metric"] == "cube_memory_used")
        self.assertEqual(
            rec,
            {
                "Category": "by_cube",
                "CubeName": "plan_BudgetPlan",
                "Metric": "cube_memory_used",
                "NativeName": "Total Memory Used",
                "Value": 8385536,
                "Unit": "B",
                "ReplicaID": 0,
                "TimeInterval": "LATEST",
                "Timestamp": None,
            },
        )

    def test_by_cube_has_no_v12_only_columns(self):
        rec = shape_v11_gauge_records(self.by_cube, category="by_cube")[0]
        self.assertNotIn("DatabaseName", rec)
        self.assertNotIn("DatabaseID", rec)

    def test_by_server_reads_time_bucket_from_slicer_axis(self):
        # v11 surfaces the MDX WHERE slicer as an axis, so the LATEST bucket is
        # read off that axis (not synthesized).
        records = shape_v11_gauge_records(self.by_server, category="by_server")
        self.assertEqual(len(records), 4)
        for rec in records:
            self.assertEqual(rec["Category"], "by_server")
            self.assertTrue(rec["Metric"].startswith("replica_"))
            self.assertEqual(rec["ReplicaID"], 0)
            self.assertEqual(rec["TimeInterval"], "LATEST")
            self.assertNotIn("CubeName", rec)

    def test_specific_time_bucket_is_read_from_slicer_axis(self):
        # Regression: a specific (non-LATEST) bucket is sliced in WHERE, which
        # v11 returns as a cardinality-1 axis; it must be read per-row, never
        # defaulted to LATEST. Built to mirror the live cellset shape.
        cellset = {
            "Axes": [
                _axis(0, [[_member("}StatsStatsForServer", "Memory Used")]]),
                _axis(1, [[_member("}TimeIntervals", "0M05")]]),
            ],
            "Cells": [{"Value": 123}],
        }
        records = shape_v11_gauge_records(cellset, category="by_server")
        self.assertEqual([r["TimeInterval"] for r in records], ["0M05"])

    def test_by_server_values_passthrough_including_none(self):
        records = shape_v11_gauge_records(self.by_server, category="by_server")
        by_metric = {r["Metric"]: r for r in records}
        # memory is a live, drifting gauge — assert verbatim numeric passthrough
        # and unit, not a magic snapshot value
        self.assertIsInstance(by_metric["replica_memory_used"]["Value"], int)
        self.assertGreater(by_metric["replica_memory_used"]["Value"], 0)
        self.assertEqual(by_metric["replica_memory_used"]["Unit"], "B")
        self.assertEqual(by_metric["replica_num_connected_clients"]["Value"], 2)
        self.assertEqual(by_metric["replica_num_connected_clients"]["Unit"], "#")
        # null cell passes through as None (the point of this test)
        self.assertIsNone(by_metric["replica_num_active_threads"]["Value"])

    def test_empty_cellset_yields_no_records(self):
        empty = {"Axes": [{"Ordinal": 0, "Tuples": []}, {"Ordinal": 1, "Tuples": []}], "Cells": []}
        self.assertEqual(shape_v11_gauge_records(empty, category="by_cube"), [])


# ====================================================================== #
# unit tests — v11 entity record shaper
# ====================================================================== #


class TestV11EntityShaper(unittest.TestCase):
    """by_rule entity-wide shaping. }StatsByRule dims [}Cubes, }LineNumber, }RuleStats]."""

    RULE_MEASURES = [
        "Rule Text",
        "Total Run Count",
        "Min Time (ms)",
        "Max Time (ms)",
        "Avg Time (ms)",
        "Total Time (ms)",
        "Last Run Time",
    ]

    def _build_by_rule_cellset(self):
        measures = _axis(0, [[_member("}RuleStats", m)] for m in self.RULE_MEASURES])
        rows = _axis(
            1,
            [
                [_member("}Cubes", "plan_BudgetPlan"), _member("}LineNumber", "1")],
                [_member("}Cubes", "plan_BudgetPlan"), _member("}LineNumber", "2")],
            ],
        )
        # axis 0 (measures, size 7) varies fastest; row r -> cells[r*7 : r*7+7]
        values = [
            ["['plan_BudgetPlan'] = 1;", 10, 1, 5, 3, 30, "2026-05-08T10:00:00"],
            ["['plan_BudgetPlan'] = 2;", 4, 2, 8, 5, 20, "2026-05-08T11:00:00"],
        ]
        cells = [{"Value": v} for row in values for v in row]
        return {"Axes": [measures, rows], "Cells": cells}

    def test_by_rule_one_row_per_cube_line(self):
        records = shape_v11_entity_records(self._build_by_rule_cellset(), category="by_rule")
        self.assertEqual(len(records), 2)
        self.assertEqual(
            records[0],
            {
                "Category": "by_rule",
                "CubeName": "plan_BudgetPlan",
                "LineNumber": "1",
                "ReplicaID": 0,
                "TimeInterval": "LATEST",
                "RuleText": "['plan_BudgetPlan'] = 1;",
                "TotalRunCount": 10,
                "MinTimeMs": 1,
                "MaxTimeMs": 5,
                "AvgTimeMs": 3,
                "TotalTimeMs": 30,
                "LastRunTime": "2026-05-08T10:00:00",
            },
        )

    def test_by_rule_columns_are_stable(self):
        records = shape_v11_entity_records(self._build_by_rule_cellset(), category="by_rule")
        expected_keys = [
            "Category",
            "CubeName",
            "LineNumber",
            "ReplicaID",
            "TimeInterval",
            "RuleText",
            "TotalRunCount",
            "MinTimeMs",
            "MaxTimeMs",
            "AvgTimeMs",
            "TotalTimeMs",
            "LastRunTime",
        ]
        self.assertEqual(list(records[0].keys()), expected_keys)

    def test_empty_cellset_yields_no_records(self):
        empty = {"Axes": [_axis(0, []), _axis(1, [])], "Cells": []}
        self.assertEqual(shape_v11_entity_records(empty, category="by_rule"), [])


class TestV11EntityShaperByCubeByClient(unittest.TestCase):
    """by_cube_by_client entity-wide shaping over a 3-dim entity crossjoin.

    }StatsByCubeByClient rows are keyed by (}PerfCubes, }PerfClients,
    }Cube Functions); each measure becomes a column. Verifies the crossjoin
    groups into one row per entity tuple (not per cell).
    """

    def _cellset(self):
        measures = _axis(
            0,
            [
                [_member("}StatsStatsByCubeByClient", "Count")],
                [_member("}StatsStatsByCubeByClient", "Elapse Time (ms)")],
            ],
        )
        rows = _axis(
            1,
            [
                [
                    _member("}PerfCubes", "plan_BudgetPlan"),
                    _member("}PerfClients", "admin"),
                    _member("}Cube Functions", "Retrieve"),
                ],
                [
                    _member("}PerfCubes", "Sales"),
                    _member("}PerfClients", "user1"),
                    _member("}Cube Functions", "Calculate"),
                ],
            ],
        )
        # v11 returns the LATEST WHERE-slicer as a cardinality-1 axis
        time = _axis(2, [[_member("}TimeIntervals", "LATEST")]])
        # axis 0 (measures, size 2) fastest; entity e -> cells[e*2 : e*2+2]
        cells = [{"Value": 100}, {"Value": 250}, {"Value": 5}, {"Value": 12}]
        return {"Axes": [measures, rows, time], "Cells": cells}

    def test_one_row_per_entity_tuple_with_both_measures(self):
        records = shape_v11_entity_records(self._cellset(), category="by_cube_by_client")
        self.assertEqual(len(records), 2)
        self.assertEqual(
            records[0],
            {
                "Category": "by_cube_by_client",
                "CubeName": "plan_BudgetPlan",
                "ClientName": "admin",
                "CubeFunction": "Retrieve",
                "ReplicaID": 0,
                "TimeInterval": "LATEST",
                "Count": 100,
                "ElapseTimeMs": 250,
            },
        )
        # second tuple grouped independently, not merged with the first
        self.assertEqual(records[1]["CubeName"], "Sales")
        self.assertEqual(records[1]["ClientName"], "user1")
        self.assertEqual(records[1]["Count"], 5)
        self.assertEqual(records[1]["ElapseTimeMs"], 12)


# ====================================================================== #
# integration tests — MetricService against live servers
# ====================================================================== #

# common columns every gauge record carries on both versions
GAUGE_COMMON = {"Category", "Metric", "NativeName", "Value", "Unit", "ReplicaID", "TimeInterval"}
V11_ONLY_CATEGORIES = ("by_process", "by_chore", "by_client", "by_cube_by_client")


class TestMetricService(unittest.TestCase):
    v11: TM1Service = None
    v12: TM1Service = None

    @classmethod
    def setUpClass(cls):
        config = configparser.ConfigParser()
        config.read(CONFIG)
        for section in config.sections():
            try:
                tm1 = TM1Service(**config[section])
                version = tm1.version
            except Exception:
                continue
            if verify_version("12.0.0", version):
                if cls.v12 is None:
                    cls.v12 = tm1
                    continue
            elif cls.v11 is None:
                cls.v11 = tm1
                continue
            tm1.logout()

    @classmethod
    def tearDownClass(cls):
        for tm1 in (cls.v11, cls.v12):
            if tm1 is not None:
                try:
                    tm1.logout()
                except Exception:
                    pass

    def _v11(self) -> TM1Service:
        if self.v11 is None:
            self.skipTest("no v11 server available")
        return self.v11

    def _v12(self) -> TM1Service:
        if self.v12 is None:
            self.skipTest("no v12 server available")
        return self.v12

    def _assert_gauge_schema(self, records, expect_cube):
        self.assertTrue(records, "expected at least one gauge record")
        for record in records:
            self.assertTrue(GAUGE_COMMON.issubset(record.keys()))
            if expect_cube:
                self.assertIn("CubeName", record)

    # ---------------- by_cube ---------------- #

    def test_by_cube_v11_unified_schema(self):
        records = self._v11().metrics.by_cube()
        self._assert_gauge_schema(records, expect_cube=True)
        cubes = {r["CubeName"] for r in records}
        self.assertFalse(any(c.startswith("}") for c in cubes), "control cubes leaked")
        self.assertNotIn("Cubes Total", cubes)
        self.assertTrue(all(r["Metric"].startswith("cube_") for r in records))
        self.assertTrue(all(r["ReplicaID"] == 0 for r in records))

    def test_by_cube_v12_unified_schema(self):
        records = self._v12().metrics.by_cube()
        self._assert_gauge_schema(records, expect_cube=True)
        self.assertTrue(all(r["Metric"].startswith("cube_") for r in records))
        self.assertTrue(all(r["NativeName"] == r["Metric"] for r in records))

    def test_by_cube_include_control_adds_control_cubes_on_v11(self):
        tm1 = self._v11()
        default_cubes = {r["CubeName"] for r in tm1.metrics.by_cube()}
        control_cubes = {r["CubeName"] for r in tm1.metrics.by_cube(include_control=True)}
        self.assertTrue(control_cubes > default_cubes)
        self.assertTrue(any(c.startswith("}") for c in control_cubes))
        self.assertNotIn("Cubes Total", control_cubes)

    def test_by_cube_common_schema_matches_across_versions(self):
        v11_keys = set(self._v11().metrics.by_cube()[0].keys())
        v12_keys = set(self._v12().metrics.by_cube()[0].keys())
        # v12 additionally carries DatabaseName/DatabaseID; common subset must match
        self.assertTrue(GAUGE_COMMON.issubset(v11_keys & v12_keys))
        self.assertIn("CubeName", v11_keys & v12_keys)
        self.assertTrue({"DatabaseName", "DatabaseID"}.issubset(v12_keys))

    # ---------------- by_server ---------------- #

    def test_by_server_v11(self):
        records = self._v11().metrics.by_server()
        self._assert_gauge_schema(records, expect_cube=False)
        self.assertTrue(all(r["Metric"].startswith("replica_") for r in records))
        self.assertTrue(all(r["ReplicaID"] == 0 for r in records))

    def test_by_server_v12(self):
        records = self._v12().metrics.by_server()
        self._assert_gauge_schema(records, expect_cube=False)
        self.assertTrue(all(r["Metric"].startswith("replica_") for r in records))

    # ---------------- cross-version guards ---------------- #

    def test_v11_only_categories_raise_on_v12(self):
        tm1 = self._v12()
        for category in V11_ONLY_CATEGORIES:
            with self.subTest(category=category):
                with self.assertRaises(TM1pyVersionException):
                    getattr(tm1.metrics, category)()

    def test_v11_only_categories_return_records_on_v11(self):
        tm1 = self._v11()
        for category in V11_ONLY_CATEGORIES:
            with self.subTest(category=category):
                records = getattr(tm1.metrics, category)()
                self.assertIsInstance(records, list)

    def test_time_interval_raises_on_v12(self):
        tm1 = self._v12()
        with self.assertRaises(TM1pyVersionException):
            tm1.metrics.by_cube(time_interval="0M05")
        with self.assertRaises(TM1pyVersionException):
            tm1.metrics.by_server(time_interval="0M05")

    # ---------------- by_rule + rule-stats lifecycle ---------------- #

    def test_by_rule_returns_list_on_both_versions(self):
        for tm1 in (self.v11, self.v12):
            if tm1 is None:
                continue
            records = tm1.metrics.by_rule()
            self.assertIsInstance(records, list)
            for record in records:
                self.assertEqual(record["Category"], "by_rule")
                self.assertIn("CubeName", record)
                self.assertIn("RuleText", record)

    def test_rule_stats_lifecycle_v12(self):
        tm1 = self._v12()
        cube = next(
            (r["CubeName"] for r in tm1.metrics.by_cube() if not r["CubeName"].startswith("}")),
            None,
        )
        self.assertIsNotNone(cube, "no usable cube on v12 server")

        pre_existed = tm1.cubes.exists(tm1.metrics.STATS_BY_RULE_CUBE)
        try:
            self.assertEqual(tm1.metrics.start_collecting_rule_stats(cube).status_code, 204)
            self.assertEqual(tm1.metrics.flush_collected_rule_stats(cube).status_code, 204)
            self.assertIsInstance(tm1.metrics.by_rule(cube=cube), list)
            self.assertEqual(tm1.metrics.stop_collecting_rule_stats(cube).status_code, 204)
        finally:
            # clean up the }StatsByRule cube if the flush created it
            if not pre_existed and tm1.cubes.exists(tm1.metrics.STATS_BY_RULE_CUBE):
                tm1.cubes.delete(tm1.metrics.STATS_BY_RULE_CUBE)

    def test_lifecycle_methods_require_v12(self):
        tm1 = self._v11()
        with self.assertRaises(TM1pyVersionException):
            tm1.metrics.start_collecting_rule_stats("plan_BudgetPlan")


if __name__ == "__main__":
    unittest.main()
