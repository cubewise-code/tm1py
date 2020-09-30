import configparser
import json
import random
import unittest
from pathlib import Path

from TM1py import Subset
from TM1py.Objects import Cube, Dimension, Hierarchy, MDXView
from TM1py.Services import TM1Service
from TM1py.Utils import MDXUtils, Utils, format_url
from TM1py.Utils.MDXUtils import (
    DimensionSelection,
    _find_case_and_space_insensitive_first_occurrence,
    read_dimension_composition_from_mdx,
    read_dimension_composition_from_mdx_set,
    read_dimension_composition_from_mdx_set_or_tuple,
    read_dimension_composition_from_mdx_tuple,
    split_mdx,
)
from TM1py.Utils.Utils import dimension_hierarchy_element_tuple_from_unique_name

from .TestUtils import skip_if_no_pandas

try:
    import pandas as pd
except ImportError:
    pass

PREFIX = "TM1py_Tests_Utils_"

MDX_TEMPLATE = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
WHERE {where}
"""

MDX_TEMPLATE_SHORT = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
"""


class TestMDXUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        # Build 4 Dimensions
        cls.dim1_name = PREFIX + "Dimension1"
        cls.dim1_element_names = ["A " + str(i) for i in range(10)]
        cls.dim1 = Dimension(cls.dim1_name)
        h = Hierarchy(cls.dim1_name, cls.dim1_name)
        for element_name in cls.dim1_element_names:
            h.add_element(element_name, "Numeric")
        cls.dim1.add_hierarchy(h)

        cls.dim2_name = PREFIX + "Dimension2"
        cls.dim2_element_names = ["B " + str(i) for i in range(10)]
        cls.dim2 = Dimension(cls.dim2_name)
        h = Hierarchy(cls.dim2_name, cls.dim2_name)
        for element_name in cls.dim2_element_names:
            h.add_element(element_name, "Numeric")
        cls.dim2.add_hierarchy(h)

        cls.dim3_name = PREFIX + "Dimension3"
        cls.dim3_element_names = ["C " + str(i) for i in range(10)]
        cls.dim3 = Dimension(cls.dim3_name)
        h = Hierarchy(cls.dim3_name, cls.dim3_name)
        for element_name in cls.dim3_element_names:
            h.add_element(element_name, "Numeric")
        cls.dim3.add_hierarchy(h)

        cls.dim4_name = PREFIX + "Dimension4"
        cls.dim4_element_names = ["D " + str(i) for i in range(10)]
        cls.dim4 = Dimension(cls.dim4_name)
        h = Hierarchy(cls.dim4_name, cls.dim4_name)
        for element_name in cls.dim4_element_names:
            h.add_element(element_name, "Numeric")
        cls.dim4.add_hierarchy(h)

        # Define cube with 4 dimensions
        cls.cube_name = PREFIX + "Cube"
        cls.cube = Cube(
            name=cls.cube_name,
            dimensions=[cls.dim1_name, cls.dim2_name, cls.dim3_name, cls.dim4_name],
        )

    def setUp(self):
        if self.tm1.cubes.exists(self.cube_name):
            self.tm1.cubes.delete(self.cube_name)
        for dimension in (self.dim1, self.dim2, self.dim3, self.dim4):
            if self.tm1.dimensions.exists(dimension.name):
                self.tm1.dimensions.delete(dimension.name)
            self.tm1.dimensions.create(dimension)
        self.tm1.cubes.create(self.cube)

        # Build Subset
        self.dim4_subset_Name = PREFIX + "Subset"
        self.tm1.dimensions.subsets.create(
            Subset(
                subset_name=self.dim4_subset_Name,
                dimension_name=self.dim4_name,
                hierarchy_name=self.dim4_name,
                expression="HEAD([{}].Members, 1)".format(self.dim4_name),
            )
        )

    def tearDown(self):
        self.tm1.cubes.delete(self.cube_name)
        self.tm1.dimensions.delete(self.dim1_name)
        self.tm1.dimensions.delete(self.dim2_name)
        self.tm1.dimensions.delete(self.dim3_name)
        self.tm1.dimensions.delete(self.dim4_name)

    def test_construct_mdx(self):
        rows = [
            DimensionSelection(dimension_name=self.dim1_name),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=self.dim2_element_names
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name),
            )
        ]
        contexts = {self.dim4_name: self.dim4_element_names[0]}
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name,
            rows=rows,
            columns=columns,
            contexts=contexts,
            suppress=None,
        )
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertEqual(number_cells, 1000)

    def test_construct_mdx_no_titles(self):
        rows = [
            DimensionSelection(dimension_name=self.dim1_name),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=self.dim2_element_names
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name),
            ),
            DimensionSelection(
                dimension_name=self.dim4_name, subset=self.dim4_subset_Name
            ),
        ]
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name, rows=rows, columns=columns, suppress=None
        )
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertEqual(number_cells, 1000)

    def test_construct_mdx_suppress_zeroes(self):
        rows = [
            DimensionSelection(dimension_name=self.dim1_name),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=self.dim2_element_names
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name),
            ),
            DimensionSelection(
                dimension_name=self.dim4_name, subset=self.dim4_subset_Name
            ),
        ]
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name, rows=rows, columns=columns, suppress="BOTH"
        )
        content = self.tm1.cubes.cells.execute_mdx(mdx)
        number_cells = len(content.keys())
        self.assertLess(number_cells, 1000)

    def test_determine_selection_type(self):
        self.assertEqual(
            DimensionSelection.determine_selection_type(
                elements=["e1", "e2"], subset=None, expression=None
            ),
            DimensionSelection.ITERABLE,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(["e1", "e2"]),
            DimensionSelection.ITERABLE,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(
                elements=None, subset="something", expression=None
            ),
            DimensionSelection.SUBSET,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, "something", None),
            DimensionSelection.SUBSET,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(
                elements=None, subset=None, expression="{[d1].[e1]}"
            ),
            DimensionSelection.EXPRESSION,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, None, "{[d1].[e1]}"),
            DimensionSelection.EXPRESSION,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(
                elements=None, subset=None, expression=None
            ),
            None,
        )
        self.assertEqual(
            DimensionSelection.determine_selection_type(None, None, None), None
        )
        self.assertEqual(DimensionSelection.determine_selection_type(), None)
        self.assertRaises(
            ValueError,
            DimensionSelection.determine_selection_type,
            ["e2"],
            "subset1",
            "{[d1].[e1]}",
        )
        self.assertRaises(
            ValueError, DimensionSelection.determine_selection_type, ["e2"], "subset1"
        )
        self.assertRaises(
            ValueError,
            DimensionSelection.determine_selection_type,
            ["e2"],
            None,
            "subset1",
        )

    def test_curly_braces(self):
        self.assertEqual(MDXUtils.curly_braces("something"), "{something}")
        self.assertEqual(MDXUtils.curly_braces("something}"), "{something}")
        self.assertEqual(MDXUtils.curly_braces("{something"), "{something}")
        self.assertEqual(MDXUtils.curly_braces("{something}"), "{something}")

    def test_build_element_unique_names_without_hierarchies(self):
        dimension_names = ["dim1", "dim1"]
        element_names = ["elem1", "elem2"]
        gen = Utils.build_element_unique_names(
            dimension_names=dimension_names, element_names=element_names
        )
        element_unique_names = list(gen)
        self.assertEqual(len(element_unique_names), 2)
        self.assertTrue("[dim1].[elem1]" in element_unique_names)
        self.assertTrue("[dim1].[elem2]" in element_unique_names)

    def test_build_element_unique_names_with_hierarchies(self):
        dimension_names = ["dim1", "dim1", "dim1"]
        hierarchy_names = ["hier1", "hier2", "hier3"]
        element_names = ["elem1", "elem2", "elem3"]
        gen = Utils.build_element_unique_names(
            dimension_names=dimension_names,
            hierarchy_names=hierarchy_names,
            element_names=element_names,
        )
        element_unique_names = list(gen)
        self.assertEqual(len(element_unique_names), 3)
        self.assertTrue("[dim1].[hier1].[elem1]" in element_unique_names)
        self.assertTrue("[dim1].[hier2].[elem2]" in element_unique_names)
        self.assertTrue("[dim1].[hier3].[elem3]" in element_unique_names)

    @skip_if_no_pandas
    def test_build_pandas_multiindex_dataframe_from_cellset(self):

        rows = [
            DimensionSelection(dimension_name=self.dim1_name),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=self.dim2_element_names
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name),
            ),
            DimensionSelection(
                dimension_name=self.dim4_name, subset=self.dim4_subset_Name
            ),
        ]
        suppress = None
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name, rows=rows, columns=columns, suppress=suppress
        )
        cellset = self.tm1.cubes.cells.execute_mdx(mdx)
        df = Utils.build_pandas_dataframe_from_cellset(cellset, multiindex=True)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.shape[0] == 1000)
        self.assertTrue(df.shape[1] == 1)
        cellset = Utils.build_cellset_from_pandas_dataframe(df)
        self.assertTrue(len(cellset.keys()) == 1000)
        self.assertIsInstance(cellset, Utils.CaseAndSpaceInsensitiveTuplesDict)

    @skip_if_no_pandas
    def test_build_pandas_dataframe_from_cellset(self):

        rows = [
            DimensionSelection(dimension_name=self.dim1_name),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=self.dim2_element_names
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name,
                expression="TM1SubsetAll([{}])".format(self.dim3_name),
            ),
            DimensionSelection(
                dimension_name=self.dim4_name, subset=self.dim4_subset_Name
            ),
        ]
        suppress = None
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name, rows=rows, columns=columns, suppress=suppress
        )
        cellset = self.tm1.cubes.cells.execute_mdx(mdx)
        df = Utils.build_pandas_dataframe_from_cellset(cellset, multiindex=False)
        self.assertTrue(df.shape[0] == 1000)

        # cater for potential Sandboxes dimension on first position
        if df.columns[0] == "Sandboxes":
            self.assertTrue(df.shape[1] == 6)
        else:
            self.assertTrue(df.shape[1] == 5)

        self.assertIsInstance(df, pd.DataFrame)
        cellset = Utils.build_cellset_from_pandas_dataframe(df)
        self.assertTrue(len(cellset.keys()) == 1000)
        self.assertIsInstance(cellset, Utils.CaseAndSpaceInsensitiveTuplesDict)

    @skip_if_no_pandas
    def test_build_pandas_dataframe_empty_cellset(self):

        self.tm1.cubes.cells.write_value(
            value=0,
            cube_name=self.cube_name,
            element_tuple=(
                self.dim1_element_names[0],
                self.dim2_element_names[0],
                self.dim3_element_names[0],
                self.dim4_element_names[0],
            ),
            dimensions=(self.dim1_name, self.dim2_name, self.dim3_name, self.dim4_name),
        )
        rows = [
            DimensionSelection(
                dimension_name=self.dim1_name, elements=(self.dim1_element_names[0],)
            ),
            DimensionSelection(
                dimension_name=self.dim2_name, elements=(self.dim2_element_names[0],)
            ),
        ]
        columns = [
            DimensionSelection(
                dimension_name=self.dim3_name, elements=(self.dim3_element_names[0],)
            ),
            DimensionSelection(
                dimension_name=self.dim4_name, elements=(self.dim4_element_names[0],)
            ),
        ]
        suppress = "Both"
        mdx = MDXUtils.construct_mdx(
            cube_name=self.cube_name, rows=rows, columns=columns, suppress=suppress
        )
        empty_cellset = self.tm1.cubes.cells.execute_mdx(mdx)
        self.assertRaises(
            ValueError, Utils.build_pandas_dataframe_from_cellset, empty_cellset, True
        )
        self.assertRaises(
            ValueError, Utils.build_pandas_dataframe_from_cellset, empty_cellset, False
        )

    @unittest.skip("Not deterministic. Needs improvement.")
    def test_read_cube_name_from_mdx(self):
        all_cube_names = self.tm1.cubes.get_all_names()
        for cube_name in all_cube_names:
            private_views, public_views = self.tm1.cubes.views.get_all(cube_name)
            for view in private_views + public_views:
                mdx = view.MDX
                self.assertEqual(
                    cube_name.upper().replace(" ", ""),
                    MDXUtils.read_cube_name_from_mdx(mdx),
                )

    def test_dimension_hierarchy_element_tuple_from_unique_name(self):
        unique_element_name = "[d1].[e1]"
        (
            dimension,
            hierarchy,
            element,
        ) = dimension_hierarchy_element_tuple_from_unique_name(unique_element_name)
        self.assertEqual(dimension, "d1")
        self.assertEqual(hierarchy, "d1")
        self.assertEqual(element, "e1")

        unique_element_name = "[d1].[d1].[e1]"
        (
            dimension,
            hierarchy,
            element,
        ) = dimension_hierarchy_element_tuple_from_unique_name(unique_element_name)
        self.assertEqual(dimension, "d1")
        self.assertEqual(hierarchy, "d1")
        self.assertEqual(element, "e1")

        unique_element_name = "[d1].[leaves].[e1]"
        (
            dimension,
            hierarchy,
            element,
        ) = dimension_hierarchy_element_tuple_from_unique_name(unique_element_name)
        self.assertEqual(dimension, "d1")
        self.assertEqual(hierarchy, "leaves")
        self.assertEqual(element, "e1")

    def test_read_dimension_composition_from_mdx_simple1(self):
        mdx = MDX_TEMPLATE.format(
            rows="{{ [{}].MEMBERS }} * {{ [{}].MEMBERS }}".format(
                self.dim1_name, self.dim2_name
            ),
            columns="{{ [{}].MEMBERS }}".format(self.dim3_name),
            cube="[{}]".format(self.cube_name),
            where="([{}].[{}])".format(self.dim4_name, self.dim4_element_names[0]),
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim1_name, self.dim2_name])
        self.assertEqual(columns, [self.dim3_name])
        self.assertEqual(titles, [self.dim4_name])

    def test_read_dimension_composition_from_mdx_simple2(self):
        mdx = MDX_TEMPLATE.format(
            rows="{{ [{}].MEMBERS }}".format(self.dim3_name),
            columns="{{ [{}].MEMBERS }} * {{ [{}].MEMBERS }}".format(
                self.dim1_name, self.dim2_name
            ),
            cube="[{}]".format(self.cube_name),
            where="( [{}].[{}] )".format(self.dim4_name, self.dim4_element_names[0]),
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim3_name])
        self.assertEqual(columns, [self.dim1_name, self.dim2_name])
        self.assertEqual(titles, [self.dim4_name])

    def test_read_dimension_composition_from_mdx_simple3(self):
        mdx = MDX_TEMPLATE.format(
            rows="{[" + self.dim3_name + "].MEMBERS}",
            columns="{[" + self.dim1_name + "].MEMBERS}",
            cube="[{}]".format(self.cube_name),
            where="([{}].[{}], [{}].[{}])".format(
                self.dim4_name,
                self.dim4_element_names[0],
                self.dim2_name,
                self.dim2_element_names[0],
            ),
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim3_name])
        self.assertEqual(columns, [self.dim1_name])
        self.assertEqual(titles, [self.dim4_name, self.dim2_name])

    def test_read_dimension_composition_from_mdx_without_titles(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{["
            + self.dim1_name
            + "].MEMBERS} * {["
            + self.dim2_name
            + "].MEMBERS}",
            columns="{["
            + self.dim3_name
            + "].MEMBERS} * {["
            + self.dim4_name
            + "].MEMBERS}",
            cube="[{}]".format(self.cube_name),
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim1_name, self.dim2_name])
        self.assertEqual(columns, [self.dim3_name, self.dim4_name])

    def test_read_dimension_composition_from_mdx_asynchronous_single(self):
        mdx = MDX_TEMPLATE.format(
            rows="{(["
            + self.dim1_name
            + "].["
            + self.dim1_element_names[0]
            + "], ["
            + self.dim2_name
            + "].["
            + self.dim2_element_names[0]
            + "])}",
            columns="{[" + self.dim3_name + "].MEMBERS}",
            cube="[{}]".format(self.cube_name),
            where="([" + self.dim4_name + "].[" + self.dim4_element_names[0] + "])",
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim1_name, self.dim2_name])
        self.assertEqual(columns, [self.dim3_name])
        self.assertEqual(titles, [self.dim4_name])

    def test_read_dimension_composition_from_mdx_asynchronous_multi(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{(["
            + self.dim1_name
            + "].["
            + self.dim1_element_names[0]
            + "], ["
            + self.dim2_name
            + "].["
            + self.dim2_element_names[0]
            + "]),(["
            + self.dim1_name
            + "].["
            + self.dim1_element_names[1]
            + "], ["
            + self.dim2_name
            + "].["
            + self.dim2_element_names[1]
            + "]) }",
            columns="{(["
            + self.dim3_name
            + "].["
            + self.dim3_element_names[0]
            + "], ["
            + self.dim4_name
            + "].["
            + self.dim4_element_names[0]
            + "]),(["
            + self.dim3_name
            + "].["
            + self.dim3_element_names[1]
            + "], ["
            + self.dim4_name
            + "].["
            + self.dim4_element_names[1]
            + "]) }",
            cube="[{}]".format(self.cube_name),
        )
        cube, rows, columns, titles = read_dimension_composition_from_mdx(mdx=mdx)

        self.assertEqual(cube, self.cube_name)
        self.assertEqual(rows, [self.dim1_name, self.dim2_name])
        self.assertEqual(columns, [self.dim3_name, self.dim4_name])
        self.assertEqual(titles, [])

    def test_read_dimension_composition_from_mdx_set_or_tuple(self):
        mdx_set = "{[dim1].[element1]} * {[dim2].[element2]}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_set)
        self.assertEqual(dimensions, ["dim1", "dim2"])

        mdx_set = "{[dim1].[element1], [dim1].[element2]}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

        mdx_set = "{[dim1].Members}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

        mdx_set = "{Tm1SubsetAll([dim1])}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

        mdx_tuple = "{([dim1].[element1], [dim2].[element2])}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1", "dim2"])

        mdx_tuple = "{([dim1].[element1])}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1"])

        mdx_tuple = "{([dim1].[element1], [dim2].[element2]), ([dim1].[element8], [dim2].[element5])}"
        dimensions = read_dimension_composition_from_mdx_set_or_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1", "dim2"])

    def test_read_dimension_composition_from_mdx_set(self):
        mdx_set = "{[dim1].[element1]} * {[dim2].[element2]}"
        dimensions = read_dimension_composition_from_mdx_set(mdx_set)
        self.assertEqual(dimensions, ["dim1", "dim2"])

        mdx_set = "{[dim1].[element1], [dim1].[element2]}"
        dimensions = read_dimension_composition_from_mdx_set(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

        mdx_set = "{[dim1].Members}"
        dimensions = read_dimension_composition_from_mdx_set(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

        mdx_set = "{Tm1SubsetAll([dim1])}"
        dimensions = read_dimension_composition_from_mdx_set(mdx_set)
        self.assertEqual(dimensions, ["dim1"])

    def test_read_dimension_composition_from_mdx_tuple(self):
        mdx_tuple = "{([dim1].[element1], [dim2].[element2])}"
        dimensions = read_dimension_composition_from_mdx_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1", "dim2"])

        mdx_tuple = "{([dim1].[element1])}"
        dimensions = read_dimension_composition_from_mdx_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1"])

        mdx_tuple = "{([dim1].[element1], [dim2].[element2]), ([dim1].[element8], [dim2].[element5])}"
        dimensions = read_dimension_composition_from_mdx_tuple(mdx_tuple)
        self.assertEqual(dimensions, ["dim1", "dim2"])

    def test_split_mdx_sets(self):
        rows = "{{ [{dim1}].[elem1] , [{dim2}].[{elem2}] }}".format(
            dim1=self.dim1_name,
            elem1=self.dim1_element_names[0],
            dim2=self.dim2_name,
            elem2=self.dim2_element_names[0],
        )
        columns = "{{ [{}].MEMBERS }}".format(self.dim3_name)
        cube = "[{}]".format(self.cube_name)
        where = "([{}].[{}])".format(self.dim4_name, self.dim4_element_names[0])

        mdx = MDX_TEMPLATE.format(rows=rows, columns=columns, cube=cube, where=where)
        mdx_rows, mdx_columns, mdx_from, mdx_where = split_mdx(mdx)
        self.assertEqual(rows.replace(" ", ""), mdx_rows)
        self.assertEqual(columns.replace(" ", ""), mdx_columns)
        self.assertEqual(cube.replace(" ", ""), mdx_from)
        self.assertEqual(where.replace(" ", ""), mdx_where)

    def test_split_mdx_tuples_without_where(self):
        rows = "{{ ( [{dim1}].[{elem1}], [{dim2}].[{elem2}] ) , ( [{dim1}].[{elem3}]. [{dim2}].[{elem4}] ) }}".format(
            dim1=self.dim1_name,
            elem1=self.dim1_element_names[0],
            dim2=self.dim2_name,
            elem2=self.dim2_element_names[0],
            elem3=self.dim2_element_names[1],
            elem4=self.dim2_element_names[1],
        )
        columns = "{{([{dim3}].[{elem1}], [{dim4}].[{elem2}])}}".format(
            dim3=self.dim3_name,
            elem1=self.dim3_element_names[0],
            dim4=self.dim4_name,
            elem2=self.dim4_element_names[0],
        )
        cube = "[{}]".format(self.cube_name)
        mdx = MDX_TEMPLATE_SHORT.format(rows=rows, columns=columns, cube=cube)
        mdx_rows, mdx_columns, mdx_from, mdx_where = split_mdx(mdx)

        self.assertEqual(rows.replace(" ", ""), mdx_rows)
        self.assertEqual(columns.replace(" ", ""), mdx_columns)
        self.assertEqual(cube.replace(" ", ""), mdx_from)

    def test_split_mdx_tuples_with_where(self):
        rows = "{{ ( [{dim1}].[{elem1}], [{dim2}].[{elem2}] ) , ( [{dim1}].[{elem3}]. [{dim2}].[{elem4}] ) }}".format(
            dim1=self.dim1_name,
            elem1=self.dim1_element_names[0],
            dim2=self.dim2_name,
            elem2=self.dim2_element_names[0],
            elem3=self.dim2_element_names[1],
            elem4=self.dim2_element_names[1],
        )
        columns = "{{ ( [{dim3}].[{elem1}] ) }}".format(
            dim3=self.dim3_name, elem1=self.dim3_element_names[0]
        )
        cube = "[{}]".format(self.cube_name)
        where = "( [{dim4}].[{elem1}] )".format(
            dim4=self.dim4_name, elem1=self.dim4_element_names[0]
        )
        mdx = MDX_TEMPLATE.format(rows=rows, columns=columns, cube=cube, where=where)
        mdx_rows, mdx_columns, mdx_from, mdx_where = split_mdx(mdx)

        self.assertEqual(rows.replace(" ", ""), mdx_rows)
        self.assertEqual(columns.replace(" ", ""), mdx_columns)
        self.assertEqual(cube.replace(" ", ""), mdx_from)
        self.assertEqual(where.replace(" ", ""), mdx_where)

    def test_split_mdx_sets_and_tuples(self):
        rows = "{{ ( [{dim1}].[{elem1}], [{dim2}].[{elem2}] ) , ( [{dim1}].[{elem3}]. [{dim2}].[{elem4}] ) }}".format(
            dim1=self.dim1_name,
            elem1=self.dim1_element_names[0],
            dim2=self.dim2_name,
            elem2=self.dim2_element_names[0],
            elem3=self.dim2_element_names[1],
            elem4=self.dim2_element_names[1],
        )
        columns = "{{ Tm1SubsetAll ( [{dim3}] ) }}".format(
            dim3=self.dim3_name, elem1=self.dim3_element_names[0]
        )
        cube = "[{}]".format(self.cube_name)
        where = "( [{dim4}].[{elem2}] )".format(
            dim4=self.dim4_name, elem2=self.dim4_element_names[0]
        )
        mdx = MDX_TEMPLATE.format(rows=rows, columns=columns, cube=cube, where=where)
        mdx_rows, mdx_columns, mdx_from, mdx_where = split_mdx(mdx)

        self.assertEqual(rows.replace(" ", ""), mdx_rows)
        self.assertEqual(columns.replace(" ", ""), mdx_columns)
        self.assertEqual(cube.replace(" ", ""), mdx_from)
        self.assertEqual(where.replace(" ", ""), mdx_where)

    def test_find_case_and_space_insensitive_first_occurrence(self):
        mdx = MDX_TEMPLATE.format(
            rows="{{ [{}].MEMBERS }}".format(self.dim3_name),
            columns="{{ [{}].MEMBERS }} * {{ [{}].MEMBERS }}".format(
                self.dim1_name, self.dim2_name
            ),
            cube="[{}]".format(self.cube_name),
            where="( [{}].[{}] )".format(self.dim4_name, self.dim4_element_names[0]),
        )

        selection, rest = _find_case_and_space_insensitive_first_occurrence(
            text=mdx, pattern_start="ROWS,", pattern_end="}ON COLUMNS"
        )

        self.assertEqual(
            "ROWS,{[TM1py_Tests_Utils_Dimension1].MEMBERS}*{[TM1py_Tests_Utils_Dimension2].MEMBERS}",
            selection,
        )
        self.assertEqual(
            "FROM[TM1py_Tests_Utils_Cube]WHERE([TM1py_Tests_Utils_Dimension4].[D0])",
            rest,
        )

    def test_extract_unique_name_from_members(self):
        members = [
            {
                "UniqueName": "[Dimension3].[Dimension3].[Element 592]",
                "Element": {"UniqueName": "[Dimension3].[Dimension3].[Element 592]"},
            }
        ]
        self.assertEqual(
            Utils.extract_unique_names_from_members(members),
            ["[Dimension3].[Dimension3].[Element 592]"],
        )

        members = [
            {
                "UniqueName": "[Dimension1].[Dimension1].[Element 790]",
                "Element": {"UniqueName": "[Dimension1].[Dimension1].[Element 790]"},
            },
            {
                "UniqueName": "[Dimension2].[Dimension2].[Element 541]",
                "Element": {"UniqueName": "[Dimension2].[Dimension2].[Element 541]"},
            },
        ]
        self.assertEqual(
            Utils.extract_unique_names_from_members(members),
            [
                "[Dimension1].[Dimension1].[Element 790]",
                "[Dimension2].[Dimension2].[Element 541]",
            ],
        )

        members = [
            {
                "UniqueName": "",
                "Element": {"UniqueName": "[Dimension1].[Dimension1].[Element 790]"},
            },
            {
                "UniqueName": "",
                "Element": {"UniqueName": "[Dimension2].[Dimension2].[Element 541]"},
            },
        ]
        self.assertEqual(
            Utils.extract_unique_names_from_members(members),
            [
                "[Dimension1].[Dimension1].[Element 790]",
                "[Dimension2].[Dimension2].[Element 541]",
            ],
        )

        members = [
            {"UniqueName": "[Dimension1].[Dimension1].[Element 790]", "Element": None},
            {"UniqueName": "[Dimension2].[Dimension2].[Element 541]", "Element": None},
        ]
        self.assertEqual(
            Utils.extract_unique_names_from_members(members),
            [
                "[Dimension1].[Dimension1].[Element 790]",
                "[Dimension2].[Dimension2].[Element 541]",
            ],
        )

    def test_extract_axes_from_cellset(self):
        with open(
            Path(__file__).parent.joinpath("resources", "raw_cellset.json")
        ) as file:
            raw_cellset_as_dict = json.load(file)
            row_axis, column_axis, title_axis = Utils.extract_axes_from_cellset(
                raw_cellset_as_dict=raw_cellset_as_dict
            )
            self.assertIn("[City].[City].[NYC]", json.dumps(row_axis))
            self.assertIn("[City].[City].[Chicago]", json.dumps(row_axis))
            self.assertIn("[Date].[Date].[2017-11-26]", json.dumps(column_axis))
            self.assertIn("[Date].[Date].[2017-11-27]", json.dumps(column_axis))
            self.assertIn("[Version].[Version].[Actual]", json.dumps(title_axis))


    @unittest.skip("Not deterministic. Needs improvement.")
    def test_mdx_from_cubeview(self):
        cube_names = self.tm1.cubes.get_all_names()
        cube_name = cube_names[random.randrange(0, len(cube_names))]
        _, public_views = self.tm1.cubes.views.get_all(cube_name=cube_name)
        # if no views on cube. Recursion
        if len(public_views) == 0:
            self.test_mdx_from_cubeview()
        else:
            # random public view on random cube
            view = public_views[random.randrange(0, len(public_views))]
            # if random view is MDXView. Recursion
            if isinstance(view, MDXView):
                self.test_mdx_from_cubeview()
            else:
                # if native view has no dimensions on the columns. Recursion
                if len(view._columns) == 0:
                    self.test_mdx_from_cubeview()
                else:
                    # sum up all numeric cells in Native View
                    data_native_view = self.tm1.cubes.cells.get_view_content(
                        cube_name, view.name, private=False
                    )
                    sum_native_view = sum(
                        [
                            float(cell["Value"])
                            for cell in data_native_view.values()
                            if str(cell["Value"]).isdigit()
                        ]
                    )

                    # get mdx from native view
                    mdx = view.as_MDX
                    # sum up all numeric cells in the response of the mdx query
                    data_mdx = self.tm1.cubes.cells.execute_mdx(mdx)
                    sum_mdx = sum(
                        [
                            float(cell["Value"])
                            for cell in data_mdx.values()
                            if str(cell["Value"]).isdigit()
                        ]
                    )

                    # test it !
                    self.assertEqual(sum_mdx, sum_native_view)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()
