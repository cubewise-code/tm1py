"""Unit tests for CellService logic that can run without a live TM1 server.

Covers:
  - clear_with_dataframe: multiple hierarchies in dimension_mapping (issue #1068)
  - execute_mdx_dataframe_pivot: **kwargs forwarding (issue #1113)
"""

import unittest
from unittest.mock import MagicMock, patch, call

import pandas as pd

from TM1py.Services.CellService import CellService


def _make_cell_service():
    """Return a CellService with the REST connection mocked out."""
    rest = MagicMock()
    rest.is_data_admin = True
    rest.is_ops_admin = True
    rest.is_admin = True
    rest.version = "11.8.000"
    svc = CellService.__new__(CellService)
    svc._rest = rest
    svc._tm1_rest = rest
    return svc


class TestClearWithDataframeMultipleHierarchies(unittest.TestCase):
    """Regression test for #1068.

    When dimension_mapping maps a single dimension name to a list of hierarchies,
    the generated MDX must include *all* hierarchies, not just the last one.
    """

    def _run(self, dimension_mapping, cube="MyCube", dim_names=None):
        """Run clear_with_dataframe with mocked dependencies and return the MDX string."""
        svc = _make_cell_service()

        if dim_names is None:
            dim_names = list(dimension_mapping.keys())

        # Mock cube_service.get_dimension_names to return the cube's dimensions
        mock_cube_svc = MagicMock()
        mock_cube_svc.get_dimension_names.return_value = dim_names
        svc.get_cube_service = MagicMock(return_value=mock_cube_svc)

        # Capture the MDX passed to clear_with_mdx instead of running it
        captured = {}
        svc.clear_with_mdx = lambda cube, mdx, **kw: captured.update({"mdx": mdx})

        df = pd.DataFrame({d: ["elem1"] for d in dim_names if d not in dimension_mapping})

        svc.clear_with_dataframe(cube=cube, df=df, dimension_mapping=dimension_mapping)
        return captured.get("mdx", "")

    def test_single_hierarchy_still_works(self):
        """Sanity-check: a str mapping produces valid MDX."""
        mdx = self._run(
            dim_names=["Year", "Month", "MyDim"],
            dimension_mapping={"MyDim": "MyHierarchy"},
        )
        self.assertIn("myhierarchy", mdx.lower())

    def test_two_hierarchies_both_appear(self):
        """Both hierarchies must appear in the MDX (not just the last one)."""
        mdx = self._run(
            dim_names=["Year", "Month", "MyDim"],
            dimension_mapping={"MyDim": ["Hierarchy1", "Hierarchy2"]},
        )
        mdx_lower = mdx.lower()
        self.assertIn("hierarchy1", mdx_lower, "First hierarchy missing from MDX")
        self.assertIn("hierarchy2", mdx_lower, "Second hierarchy missing from MDX")
        # Both should appear in a UNION, not just the last one overwriting
        self.assertIn("union", mdx_lower, "Expected UNION of hierarchies in MDX")

    def test_three_hierarchies_all_appear(self):
        """All three hierarchies must appear."""
        mdx = self._run(
            dim_names=["Year", "Month", "MyDim"],
            dimension_mapping={"MyDim": ["H1", "H2", "H3"]},
        )
        mdx_lower = mdx.lower()
        for h in ("h1", "h2", "h3"):
            self.assertIn(h, mdx_lower, f"{h} missing from MDX")


class TestExecuteMdxDataframePivotKwargs(unittest.TestCase):
    """Regression test for #1113.

    execute_mdx_dataframe_pivot must forward **kwargs to extract_cellset_dataframe_pivot.
    """

    def test_kwargs_forwarded(self):
        svc = _make_cell_service()

        svc.create_cellset = MagicMock(return_value="cellset-id-123")
        svc.extract_cellset_dataframe_pivot = MagicMock(return_value=pd.DataFrame())

        svc.execute_mdx_dataframe_pivot(
            mdx="SELECT ... FROM [Cube]",
            dropna=True,
            fill_value=0,
            sandbox_name="MySandbox",
            use_compact_json=True,
        )

        svc.extract_cellset_dataframe_pivot.assert_called_once_with(
            cellset_id="cellset-id-123",
            dropna=True,
            fill_value=0,
            sandbox_name="MySandbox",
            use_compact_json=True,
        )

    def test_extra_kwargs_forwarded(self):
        """Arbitrary extra kwargs like cell_properties are forwarded."""
        svc = _make_cell_service()
        svc.create_cellset = MagicMock(return_value="cid")
        svc.extract_cellset_dataframe_pivot = MagicMock(return_value=pd.DataFrame())

        svc.execute_mdx_dataframe_pivot(
            mdx="SELECT FROM [Cube]",
            cell_properties=["FormattedValue"],
        )

        _, kwargs = svc.extract_cellset_dataframe_pivot.call_args
        self.assertIn("cell_properties", kwargs)
        self.assertEqual(kwargs["cell_properties"], ["FormattedValue"])

    def test_no_kwargs_still_works(self):
        """Calling without kwargs must not raise."""
        svc = _make_cell_service()
        svc.create_cellset = MagicMock(return_value="cid")
        svc.extract_cellset_dataframe_pivot = MagicMock(return_value=pd.DataFrame())

        result = svc.execute_mdx_dataframe_pivot(mdx="SELECT FROM [Cube]")
        self.assertIsInstance(result, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
