"""Unit tests for the pure v12 Metrics() $filter builder (Module C).

Server-free. Ports/expands the inline filter logic from PR #1396's
``MetricService.get()`` into a tested pure function.
"""

import unittest
from datetime import datetime

from TM1py.Metrics.odata_filter import build_metrics_url


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


if __name__ == "__main__":
    unittest.main()
