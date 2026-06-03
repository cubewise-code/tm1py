"""Unit tests for the pure v11 MDX builder (Module B).

Server-free. The exact MDX strings asserted here were validated against a live
v11 server (11.8) during fixture capture.
"""

import unittest

from TM1py.Metrics.mdx import ALL_TIME_INTERVALS, build_v11_mdx

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


if __name__ == "__main__":
    unittest.main()
