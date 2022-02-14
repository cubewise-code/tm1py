import unittest

from TM1py import MDXView


class TestMDXView(unittest.TestCase):
    cube_name = "c1"
    view_name = "v1"
    mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e1], [d5].[h1].[e1])
    """

    def setUp(self) -> None:
        self.view = MDXView(
            cube_name=self.cube_name,
            view_name=self.view_name,
            MDX=self.mdx)

    def test_substitute_title(self):
        self.view.substitute_title(dimension="d3", hierarchy="d3", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e2], [d4].[e1], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_different_case(self):
        self.view.substitute_title(dimension="D3", hierarchy="D3", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([D3].[D3].[e2], [d4].[e1], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_without_hierarchy(self):
        self.view.substitute_title(dimension="d4", hierarchy="d4", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e2], [d5].[h1].[e1])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_with_hierarchy(self):
        self.view.substitute_title(dimension="d5", hierarchy="h1", element="e2")
        expected_mdx = """
    SELECT
    {[d1].[e1], [d1].[e2], [d1].[e3]} ON ROWS,
    {Tm1SubsetAll([d2])} ON COLUMNS
    FROM [c1]
    WHERE ([d3].[d3].[e1], [d4].[e1], [d5].[h1].[e2])
    """
        self.assertEqual(expected_mdx, self.view.mdx)

    def test_substitute_title_value_error(self):
        with self.assertRaises(ValueError) as error:
            self.view.substitute_title(dimension="d6", hierarchy="d6", element="e2")
            print(error)
