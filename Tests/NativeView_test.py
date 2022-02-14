import unittest

from TM1py import NativeView, ViewAxisSelection, AnonymousSubset, ViewTitleSelection, Subset


class TestNativeView(unittest.TestCase):

    def test_as_mdx_happy_case(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))],
            rows=[ViewAxisSelection("d2", AnonymousSubset("d2", "d2", "{[d2].[e2]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} ON 0,\r\n"
            "{[d2].[e2]} ON 1\r\n"
            "FROM [C1]\r\n"
            "WHERE ([D3].[D3].[E3])",
            native_view.mdx)

    def test_as_mdx_multi_rows_multi_columns(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=True,
            titles=[
                ViewTitleSelection("d5", AnonymousSubset("d5", "d5", "", ["e5"]), "e5"),
                ViewTitleSelection("d6", AnonymousSubset("d6", "d6", "", ["e6"]), "e6")],
            columns=[
                ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}")),
                ViewAxisSelection("d2", AnonymousSubset("d2", "d2", "{[d2].[e2]}"))],
            rows=[
                ViewAxisSelection("d3", AnonymousSubset("d3", "d3", "{[d3].[e3]}")),
                ViewAxisSelection("d4", AnonymousSubset("d4", "d4", "{[d4].[e4]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} * {[d2].[e2]} ON 0,\r\n"
            "NON EMPTY {[d3].[e3]} * {[d4].[e4]} ON 1\r\n"
            "FROM [C1]\r\n"
            "WHERE ([D5].[D5].[E5],[D6].[D6].[E6])",
            native_view.mdx)

    def test_as_mdx_no_rows(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} ON 0\r\n"
            "FROM [C1]\r\n"
            "WHERE ([D3].[D3].[E3])",
            native_view.mdx)

    def test_as_mdx_no_columns(self):
        with self.assertRaises(ValueError) as _:
            native_view = NativeView(
                cube_name="c1",
                view_name="not_relevant",
                suppress_empty_columns=True,
                suppress_empty_rows=False,
                titles=[ViewTitleSelection("d3", AnonymousSubset("d3", "d3", "", ["e3"]), "e3")],
                rows=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

            _ = native_view.mdx

    def test_as_mdx_no_titles(self):
        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            columns=[ViewAxisSelection("d1", AnonymousSubset("d1", "d1", "{[d1].[e1]}"))])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {[d1].[e1]} ON 0\r\n"
            "FROM [C1]",
            native_view.mdx)

    def test_as_mdx_registered_subsets(self):
        s1 = Subset("s1", "d1", "d1", None, None, ["e1", "e2"])
        s2 = Subset("s2", "d2", "d2", None, None, ["e1", "e2"])
        s3 = Subset("s3", "d3", "d3", None, None, ["e1", "e2"])

        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d1", s1, "e1")],
            columns=[ViewAxisSelection("d2", s2)],
            rows=[ViewAxisSelection("d3", s3)])

        self.assertEqual(
            "SELECT\r\n"
            "NON EMPTY {TM1SUBSETTOSET([D2].[D2],\"s2\")} ON 0,\r\n"
            "{TM1SUBSETTOSET([D3].[D3],\"s3\")} ON 1\r\n"
            "FROM [C1]\r\n"
            "WHERE ([D1].[D1].[E1])",
            native_view.mdx)

    def test_substitute_title(self):
        s1 = Subset("s1", "d1", "d1", None, None, ["e1", "e2"])
        s2 = Subset("s2", "d2", "d2", None, None, ["e1", "e2"])
        s3 = Subset("s3", "d3", "d3", None, None, ["e1", "e2"])

        native_view = NativeView(
            cube_name="c1",
            view_name="not_relevant",
            suppress_empty_columns=True,
            suppress_empty_rows=False,
            titles=[ViewTitleSelection("d1", s1, "e1")],
            columns=[ViewAxisSelection("d2", s2)],
            rows=[ViewAxisSelection("d3", s3)])

        native_view.substitute_title("d1", "e2")

        self.assertEqual(native_view.titles[0].selected, "e2")
