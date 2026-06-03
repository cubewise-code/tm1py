"""Unit tests for the pure metric vocabulary / normalizer module (Module A).

Server-free. Test cases derive directly from the canonical mapping tables in
CONTEXT.md ("Canonical metric vocabulary (gauge categories)").
"""

import unittest

from TM1py.Metrics.vocabulary import (
    CATEGORY_BY_CUBE,
    CATEGORY_BY_SERVER,
    UNIT_BYTES,
    UNIT_COUNT,
    normalize_v11_measure,
    v11_measure_names,
)


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


if __name__ == "__main__":
    unittest.main()
