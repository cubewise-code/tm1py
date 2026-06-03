"""Integration tests for MetricService (Modules E & F).

Runs against the live servers in ``config.ini``. Connections are classified by
version at setup, so the same suite asserts the unified schema on both a v11
and a v12 server. Each test skips cleanly when the relevant server is absent.
"""

import configparser
import unittest
from pathlib import Path

from TM1py import TM1Service
from TM1py.Exceptions.Exceptions import TM1pyVersionException
from TM1py.Utils.Utils import verify_version

CONFIG = Path(__file__).parent / "config.ini"

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
