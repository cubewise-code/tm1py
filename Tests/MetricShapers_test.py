"""Unit tests for the pure record shapers (Module D).

Server-free. Driven by fixtures captured once from a live v12 server
(``Tests/resources/metrics/v12_metrics_raw.json``) plus small hand-built
payloads for exact-value assertions.
"""

import json
import unittest
from pathlib import Path

from TM1py.Metrics.shapers import (
    shape_v11_entity_records,
    shape_v11_gauge_records,
    shape_v12_gauge_records,
)


def _member(dim, name):
    return {"Name": name, "UniqueName": f"[{dim}].[{dim}].[{name}]"}


def _axis(ordinal, tuples_members):
    return {"Ordinal": ordinal, "Tuples": [{"Members": members} for members in tuples_members]}


FIXTURES = Path(__file__).parent / "resources" / "metrics"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


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


if __name__ == "__main__":
    unittest.main()
