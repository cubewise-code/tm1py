import configparser
import types
import unittest
from pathlib import Path

import pandas as pd
import pytest

from TM1py.Exceptions.Exceptions import TM1pyException
from TM1py.Objects import MDXView, Cube, Dimension, Element, Hierarchy, NativeView, AnonymousSubset, ElementAttribute
from TM1py.Services import TM1Service
from TM1py.Utils import Utils, abbreviate_mdx

# Hard coded stuff
PREFIX = 'TM1py_Tests_Cell_'
CUBE_NAME = PREFIX + "Cube"
VIEW_NAME = PREFIX + "View"
DIMENSION_NAMES = [
    PREFIX + 'Dimension1',
    PREFIX + 'Dimension2',
    PREFIX + 'Dimension3']
STRING_CUBE_NAME = PREFIX + "StringCube"
STRING_DIMENSION_NAMES = [
    PREFIX + 'StringDimension1',
    PREFIX + 'StringDimension2',
    PREFIX + 'StringDimension3']
CELLS_IN_STRING_CUBE = {
    ('d1e1', 'd2e1', 'd3e1'): 'String1',
    ('d1e2', 'd2e2', 'd3e2'): 'String2',
    ('d1e3', 'd2e3', 'd3e3'): 'String3'}

LATIN_1_ENCODED_TEXT = "Èd5áÂè"

CUBE_NAME_RPS1 = PREFIX + "Cube" + "_RPS1"
CUBE_NAME_RPS2 = PREFIX + "Cube" + "_RPS2"
DIMENSION_NAME_RPS1 = PREFIX + "Dimension" + "_RPS1"
DIMENSION_NAME_RPS2 = PREFIX + "Dimension" + "_RPS2"

MDX_TEMPLATE = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
WHERE {where}
"""

MDX_TEMPLATE_NON_EMPTY = """
SELECT 
NON EMPTY {rows} ON ROWS,
NON EMPTY {columns} ON COLUMNS
FROM {cube}
WHERE {where}
"""

MDX_TEMPLATE_SHORT = """
SELECT 
{rows} ON ROWS,
{columns} ON COLUMNS
FROM {cube}
"""

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))


class TestDataMethods(unittest.TestCase):
    tm1 = None

    # Setup Cubes, Dimensions and Subsets
    @classmethod
    def setup_class(cls):
        # Connection to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # Build Dimensions
        for dimension_name in DIMENSION_NAMES:
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            element_attributes = [ElementAttribute("Attr1", "String"),
                                  ElementAttribute("Attr2", "Numeric"),
                                  ElementAttribute("Attr3", "Numeric")]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements,
                                  element_attributes=element_attributes)
            dimension = Dimension(dimension_name, [hierarchy])
            if cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.update(dimension)
            else:
                cls.tm1.dimensions.create(dimension)
            attribute_cube = "}ElementAttributes_" + dimension_name
            attribute_values = dict()
            for element in elements:
                attribute_values[(element.name, "Attr1")] = "TM1py"
                attribute_values[(element.name, "Attr2")] = "2"
                attribute_values[(element.name, "Attr3")] = "3"
            cls.tm1.cubes.cells.write_values(attribute_cube, attribute_values)

        # Build Cube
        cube = Cube(CUBE_NAME, DIMENSION_NAMES)
        if not cls.tm1.cubes.exists(CUBE_NAME):
            cls.tm1.cubes.create(cube)

        # Build cube view
        view = NativeView(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            suppress_empty_columns=True,
            suppress_empty_rows=True)
        view.add_row(
            dimension_name=DIMENSION_NAMES[0],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[0],
                expression='{[' + DIMENSION_NAMES[0] + '].Members}'))
        view.add_row(
            dimension_name=DIMENSION_NAMES[1],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[1],
                expression='{[' + DIMENSION_NAMES[1] + '].Members}'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[2],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[2],
                expression='{[' + DIMENSION_NAMES[2] + '].Members}'))
        if not cls.tm1.cubes.views.exists(CUBE_NAME, view.name, private=False):
            cls.tm1.cubes.views.create(
                view=view,
                private=False)

        # build target coordinates
        cls.target_coordinates = list(zip(('Element ' + str(e) for e in range(1, 101)),
                                          ('Element ' + str(e) for e in range(1, 101)),
                                          ('Element ' + str(e) for e in range(1, 101))))

        # cellset of data that shall be written
        cls.cellset = Utils.CaseAndSpaceInsensitiveTuplesDict()
        for element1, element2, element3 in cls.target_coordinates:
            value = 1
            cls.cellset[(element1, element2, element3)] = value

        # Sum of all the values that we write in the cube. serves as a checksum.
        cls.total_value = sum(cls.cellset.values())

        # Fill cube with values
        cls.tm1.cubes.cells.write_values(CUBE_NAME, cls.cellset)

        # For tests on string related methods
        cls.build_string_cube()

    @classmethod
    def build_string_cube(cls):
        for d, dimension_name in enumerate(STRING_DIMENSION_NAMES, start=1):
            dimension = Dimension(dimension_name)
            hierarchy = Hierarchy(dimension_name, dimension_name)
            for i in range(1, 5, 1):
                element_name = "d" + str(d) + "e" + str(i)
                hierarchy.add_element(element_name=element_name, element_type="String")
            dimension.add_hierarchy(hierarchy)
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.create(dimension)

        cube = Cube(name=STRING_CUBE_NAME, dimensions=STRING_DIMENSION_NAMES)
        if not cls.tm1.cubes.exists(cube.name):
            cls.tm1.cubes.create(cube)
        # zero out cube
        cls.tm1.processes.execute_ti_code("CubeClearData('" + STRING_CUBE_NAME + "');")

        cls.tm1.cubes.cells.write_values(STRING_CUBE_NAME, CELLS_IN_STRING_CUBE)

    @classmethod
    def remove_string_cube(cls):
        if cls.tm1.cubes.exists(cube_name=STRING_CUBE_NAME):
            cls.tm1.cubes.delete(cube_name=STRING_CUBE_NAME)
        for dimension_name in STRING_DIMENSION_NAMES:
            if cls.tm1.dimensions.exists(dimension_name=dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def build_assets_for_relative_proportional_spread_tests(cls):
        for dimension_name in (DIMENSION_NAME_RPS1, DIMENSION_NAME_RPS2):
            dimension = Dimension(dimension_name)
            hierarchy = Hierarchy(dimension_name, dimension_name)
            hierarchy.add_element(element_name="c1", element_type="Consolidated")
            for i in range(1, 5, 1):
                element_name = "e" + str(i)
                hierarchy.add_element(element_name=element_name, element_type="Numeric")
                hierarchy.add_edge(parent="c1", component=element_name, weight=1)
            dimension.add_hierarchy(hierarchy)
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.create(dimension)

        for cube_name in (CUBE_NAME_RPS1, CUBE_NAME_RPS2):
            cube = Cube(name=cube_name, dimensions=(DIMENSION_NAME_RPS1, DIMENSION_NAME_RPS2))
            if not cls.tm1.cubes.exists(cube.name):
                cls.tm1.cubes.create(cube)
            # zero out cube
            cls.tm1.processes.execute_ti_code("CubeClearData('" + cube_name + "');")

    @classmethod
    def remove_assets_for_relative_proportional_spread_tests(cls):
        for cube_name in (CUBE_NAME_RPS1, CUBE_NAME_RPS2):
            if cls.tm1.cubes.exists(cube_name):
                cls.tm1.cubes.delete(cube_name=cube_name)
        for dimension_name in (DIMENSION_NAME_RPS1, DIMENSION_NAME_RPS2):
            if cls.tm1.dimensions.exists(dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    def test_write_and_get_value(self):
        original_value = self.tm1.cubes.cells.get_value(CUBE_NAME, 'Element1,EleMent2,ELEMENT  3')
        response = self.tm1.cubes.cells.write_value(1, CUBE_NAME, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(CUBE_NAME, 'Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, 1)
        response = self.tm1.cubes.cells.write_value(2, CUBE_NAME, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(CUBE_NAME, 'Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, 2)
        self.tm1.cubes.cells.write_value(original_value, CUBE_NAME, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_write_values(self):
        response = self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)
        self.assertTrue(response.ok)

    def test_relative_proportional_spread_happy_case(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_NAME_RPS1, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_NAME_RPS1,
            unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[e2]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"),
            reference_cube=CUBE_NAME_RPS1,
            reference_unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[c1]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"))

        rows = "[" + DIMENSION_NAME_RPS1 + "].[e2]"
        columns = ",".join("[" + DIMENSION_NAME_RPS2 + "].[" + elem + "]" for elem in ("e1", "e2", "e3"))
        mdx = """
        SELECT 
        {{ {rows} }} ON 0,
        {{ {columns} }} ON 1
        FROM {cube}
        """.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME_RPS1)
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(next(values), 2)
        self.assertEqual(next(values), 4)
        self.assertEqual(next(values), 6)

    def test_relative_proportional_with_explicit_hierarchies(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_NAME_RPS1, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_NAME_RPS1,
            unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[" + DIMENSION_NAME_RPS1 + "].[e2]",
                                  "[" + DIMENSION_NAME_RPS2 + "].[" + DIMENSION_NAME_RPS2 + "].[c1]"),
            reference_cube=CUBE_NAME_RPS1,
            reference_unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[" + DIMENSION_NAME_RPS1 + "].[c1]",
                                            "[" + DIMENSION_NAME_RPS2 + "].[" + DIMENSION_NAME_RPS2 + "].[c1]"))

        rows = "[" + DIMENSION_NAME_RPS1 + "].[e2]"
        columns = ",".join("[" + DIMENSION_NAME_RPS2 + "].[" + elem + "]" for elem in ("e1", "e2", "e3"))
        mdx = """
        SELECT 
        {{ {rows} }} ON 0,
        {{ {columns} }} ON 1
        FROM {cube}
        """.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME_RPS1)
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(next(values), 2)
        self.assertEqual(next(values), 4)
        self.assertEqual(next(values), 6)

    def test_relative_proportional_spread_without_reference_cube(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_NAME_RPS1, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_NAME_RPS1,
            unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[e2]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"),
            reference_unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[c1]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"))

        rows = "[" + DIMENSION_NAME_RPS1 + "].[e2]"
        columns = ",".join("[" + DIMENSION_NAME_RPS2 + "].[" + elem + "]" for elem in ("e1", "e2", "e3"))
        mdx = """
        SELECT 
        {{ {rows} }} ON 0,
        {{ {columns} }} ON 1
        FROM {cube}
        """.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME_RPS1)
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(next(values), 2)
        self.assertEqual(next(values), 4)
        self.assertEqual(next(values), 6)

    def test_relative_proportional_spread_with_different_reference_cube(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_NAME_RPS2, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_NAME_RPS1,
            unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[e2]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"),
            reference_cube=CUBE_NAME_RPS2,
            reference_unique_element_names=("[" + DIMENSION_NAME_RPS1 + "].[c1]", "[" + DIMENSION_NAME_RPS2 + "].[c1]"))

        rows = "[" + DIMENSION_NAME_RPS1 + "].[e2]"
        columns = ",".join("[" + DIMENSION_NAME_RPS2 + "].[" + elem + "]" for elem in ("e1", "e2", "e3"))
        mdx = """
        SELECT 
        {{ {rows} }} ON 0,
        {{ {columns} }} ON 1
        FROM {cube}
        """.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME_RPS1)
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(next(values), 2)
        self.assertEqual(next(values), 4)
        self.assertEqual(next(values), 6)

    def test_execute_mdx(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = """
        SELECT
        NON EMPTY {rows} ON ROWS,
        NON EMPTY {columns} ON COLUMNS
        FROM
        [{cube}]
        """.format(
            rows="{[" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members}",
            columns="{[" + DIMENSION_NAMES[2] + "].MEMBERS}",
            cube=CUBE_NAME)
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(self.total_value, sum([v["Value"] for v in data.values() if v["Value"]]))

        # MDX with top
        data = self.tm1.cubes.cells.execute_mdx(mdx, top=5)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(len(data), 5)

        # MDX Query with calculated MEMBER
        mdx = """
        WITH MEMBER[{}].[{}] AS 2 
        SELECT[{}].MEMBERS ON ROWS, 
        {{[{}].[{}]}} ON COLUMNS 
        FROM[{}] 
        WHERE([{}].DefaultMember)""".format(
            DIMENSION_NAMES[1], "Calculated Member", DIMENSION_NAMES[0],
            DIMENSION_NAMES[1], "Calculated Member", CUBE_NAME, DIMENSION_NAMES[2])

        data = self.tm1.cubes.cells.execute_mdx(mdx, cell_properties=["Value", "Ordinal"])
        self.assertEqual(1000, len(data))
        self.assertEqual(2000, sum(v["Value"] for v in data.values()))
        self.assertEqual(
            sum(range(0, 1000)),
            sum(v["Ordinal"] for v in data.values()))

    def test_execute_mdx_without_rows(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        rows = "{}"
        columns = "{{ [{}].Members * [{}].Members * [{}].MEMBERS }}".format(*DIMENSION_NAMES)

        # MDX Query that gets full cube content with zero suppression
        mdx = """
            SELECT
            NON EMPTY {rows} ON ROWS,
            NON EMPTY {columns} ON COLUMNS
            FROM
            [{cube}]
            """.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME)
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(self.total_value, sum([v["Value"] for v in data.values() if v["Value"]]))
        for coordinates in data.keys():
            self.assertEqual(len(coordinates), 3)
            self.assertIn("[TM1py_Tests_Cell_Dimension1].", coordinates[0])
            self.assertIn("[TM1py_Tests_Cell_Dimension2].", coordinates[1])
            self.assertIn("[TM1py_Tests_Cell_Dimension3].", coordinates[2])

    def test_execute_mdx_without_columns(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = """
            SELECT
            NON EMPTY {rows} ON ROWS,
            NON EMPTY {columns} ON COLUMNS
            FROM
            [{cube}]
            """.format(
            rows="{{ [{}].Members * [{}].Members * [{}].MEMBERS }}".format(*DIMENSION_NAMES),
            columns="{}",
            cube=CUBE_NAME)
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(self.total_value, sum([v["Value"] for v in data.values() if v["Value"]]))
        for coordinates in data.keys():
            self.assertEqual(len(coordinates), 3)
            self.assertIn("[TM1py_Tests_Cell_Dimension1].", coordinates[0])
            self.assertIn("[TM1py_Tests_Cell_Dimension2].", coordinates[1])
            self.assertIn("[TM1py_Tests_Cell_Dimension3].", coordinates[2])

    def test_execute_mdx_skip_contexts(self):
        mdx = MDX_TEMPLATE.format(
            rows="{[" + DIMENSION_NAMES[0] + "].[Element1]}",
            columns="{[" + DIMENSION_NAMES[1] + "].[Element1]}",
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")
        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_contexts=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                DIMENSION_NAMES[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                DIMENSION_NAMES[1])

    def test_execute_mdx_raw_skip_contexts(self):
        mdx = MDX_TEMPLATE.format(
            rows="{[" + DIMENSION_NAMES[0] + "].[Element1]}",
            columns="{[" + DIMENSION_NAMES[1] + "].[Element1]}",
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")

        raw_response = self.tm1.cubes.cells.execute_mdx_raw(
            mdx,
            skip_contexts=True,
            member_properties=["UniqueName"])

        self.assertEqual(len(raw_response["Axes"]), 2)
        for axis in raw_response["Axes"]:
            dimension_on_axis = Utils.dimension_name_from_element_unique_name(
                axis["Tuples"][0]["Members"][0]["UniqueName"])
            self.assertNotEqual(dimension_on_axis, DIMENSION_NAMES[2])

    def test_execute_mdx_rows_and_values_one_cell(self):
        rows = """
             {{ [{dim0}].[Element1] }}
            """.format(dim0=DIMENSION_NAMES[0])

        columns = """
             {{ [{dim1}].[Element1] }}
            """.format(dim1=DIMENSION_NAMES[1])

        mdx = MDX_TEMPLATE.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            self.assertEqual(len(cells), 1)

    def test_execute_mdx_rows_and_values_empty_cellset(self):
        # make sure it's empty
        self.tm1.cubes.cells.write_values(CUBE_NAME, {("Element1", "Element1", "Element1"): 0})

        rows = """
             {{ [{dim0}].[Element1] }}
            """.format(dim0=DIMENSION_NAMES[0])

        columns = """
             {{ [{dim1}].[Element1] }}
            """.format(dim1=DIMENSION_NAMES[1])

        mdx = MDX_TEMPLATE_NON_EMPTY.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)
        self.assertEqual(len(data), 0)

    def test_execute_mdx_rows_and_values_member_names(self):
        rows = """
             {{ [{dim0}].[Element1] }}
            """.format(dim0=DIMENSION_NAMES[0])

        columns = """
             {{ [{dim1}].[Element1] }}
            """.format(dim1=DIMENSION_NAMES[1])

        mdx = MDX_TEMPLATE.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=False)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            member_name = row[0]
            self.assertEqual(member_name, "Element 1")

    def test_execute_mdx_rows_and_values_one_dimension_on_rows(self):
        rows = """
             {{ [{dim0}].[Element1], [{dim0}].[Element2] }}
            """.format(dim0=DIMENSION_NAMES[0])

        columns = """
             {{ [{dim1}].[Element1], [{dim1}].[Element2], [{dim1}].[Element3] }}
            """.format(dim1=DIMENSION_NAMES[1])

        mdx = MDX_TEMPLATE.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME,
            where="[" + DIMENSION_NAMES[2] + "].[Element1]")
        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx)

        self.assertEqual(len(data), 2)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            self.assertEqual(len(cells), 3)

    def test_execute_mdx_rows_and_values_two_dimensions_on_rows(self):
        rows = """
            {{ [{dim0}].[Element1], [{dim0}].[Element2] }} * {{ [{dim1}].[Element1], [{dim1}].[Element2] }}
            """.format(dim0=DIMENSION_NAMES[0], dim1=DIMENSION_NAMES[1])

        columns = """
             {{ [{dim2}].[Element1], [{dim2}].[Element2], [{dim2}].[Element3] }}
            """.format(dim2=DIMENSION_NAMES[2])

        mdx = MDX_TEMPLATE_SHORT.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME)
        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx)

        self.assertEqual(len(data), 4)
        for row, cells in data.items():
            self.assertEqual(len(row), 2)
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            dimension = Utils.dimension_name_from_element_unique_name(row[1])
            self.assertEqual(dimension, DIMENSION_NAMES[1])
            self.assertEqual(len(cells), 3)

    def test_execute_mdx_raw_with_member_properties_with_elem_properties(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        raw = self.tm1.cubes.cells.execute_mdx_raw(
            mdx=mdx,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"],
            member_properties=["Name", "Ordinal", "Weight"])
        cells = raw["Cells"]
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    self.assertIn("Name", member)
                    self.assertIn("Ordinal", member)
                    self.assertIn("Weight", member)
                    self.assertNotIn("Type", member)
                    element = member["Element"]
                    self.assertIn("Name", element)
                    self.assertIn("UniqueName", element)
                    self.assertNotIn("Type", element)
                    self.assertIn("Attr1", element["Attributes"])
                    self.assertIn("Attr2", element["Attributes"])
                    self.assertNotIn("Attr3", element["Attributes"])
                    self.assertEqual(element["Attributes"]["Attr1"], "TM1py")
                    self.assertEqual(element["Attributes"]["Attr2"], 2)

    def test_execute_mdx_raw_with_member_properties_without_elem_properties(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        raw = self.tm1.cubes.cells.execute_mdx_raw(
            mdx=mdx,
            cell_properties=["Value", "RuleDerived"],
            member_properties=["Name", "Ordinal", "Weight"])
        cells = raw["Cells"]
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    self.assertIn("Name", member)
                    self.assertIn("Ordinal", member)
                    self.assertIn("Weight", member)
                    self.assertNotIn("Type", member)
                    self.assertNotIn("Element", member)

    def test_execute_mdx_raw_without_member_properties_with_elem_properties(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        raw = self.tm1.cubes.cells.execute_mdx_raw(
            mdx=mdx,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "Type"],
            member_properties=None)
        cells = raw["Cells"]
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    element = member["Element"]
                    self.assertIn("Name", element)
                    self.assertIn("Type", element)
                    self.assertNotIn("UniqueName", element)
                    self.assertNotIn("UniqueName", member)
                    self.assertNotIn("Ordinal", member)

    def test_execute_mdx_values(self):
        self.tm1.cells.write_values(CUBE_NAME, self.cellset)

        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS * [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)

        cell_values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertIsInstance(
            cell_values,
            types.GeneratorType)
        # Check if total value is the same. Handle None.
        self.assertEqual(
            self.total_value,
            sum([v for v in cell_values if v]))
        # Define MDX Query with calculated MEMBER
        mdx = "WITH MEMBER[{}].[{}] AS 2 " \
              "SELECT[{}].MEMBERS ON ROWS, " \
              "{{[{}].[{}]}} ON COLUMNS " \
              "FROM[{}] " \
              "WHERE([{}].DefaultMember)".format(DIMENSION_NAMES[1], "Calculated Member", DIMENSION_NAMES[0],
                                                 DIMENSION_NAMES[1], "Calculated Member", CUBE_NAME, DIMENSION_NAMES[2])

        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            1000,
            len(list(data)))
        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            2000,
            sum(data))

    def test_execute_mdx_csv(self):
        # Simple MDX
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check type
        self.assertIsInstance(csv, str)
        records = csv.split('\r\n')[1:]
        coordinates = {tuple(record.split(',')[0:3])
                       for record
                       in records if record != '' and records[4] != 0}

        # check number of coordinates (with values)
        self.assertEqual(
            len(coordinates),
            len(self.target_coordinates))

        # check if coordinates are the same
        self.assertTrue(coordinates.issubset(self.target_coordinates))
        values = [float(record.split(',')[3])
                  for record
                  in records if record != '']

        # check if sum of retrieved values is sum of written values
        self.assertEqual(
            self.total_value,
            sum(values))

        # MDX Query with calculated MEMBER
        mdx_template = """
                WITH MEMBER[{dim1}].[{calculated_member}] AS [{attribute_cube}].({attribute})
                SELECT[{dim0}].MEMBERS ON ROWS, 
                {{[{dim1}].[{calculated_member}]}} ON COLUMNS 
                FROM[{cube_name}] 
                WHERE([{dim2}].DefaultMember)
            """
        mdx = mdx_template.format(
            cube_name=CUBE_NAME,
            dim0=DIMENSION_NAMES[0],
            dim1=DIMENSION_NAMES[1],
            dim2=DIMENSION_NAMES[2],
            calculated_member="Calculated Member",
            attribute_cube="}ElementAttributes_" + DIMENSION_NAMES[0],
            attribute="[}ElementAttributes_" + DIMENSION_NAMES[0] + "].[Attr3]")
        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check type
        records = csv.split('\r\n')[1:]
        coordinates = {tuple(record.split(',')[0:2])
                       for record
                       in records if record != '' and records[4] != 0}

        # check number of coordinates (with values)
        self.assertEqual(len(coordinates), 1000)

        # Check if retrieved values are equal to attribute value
        values = [float(record.split(',')[2])
                  for record
                  in records if record != ""]
        for value in values:
            self.assertEqual(value, 3)

    def test_execute_mdx_dataframe(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {
            tuple(row)
            for row
            in df[[*DIMENSION_NAMES]].values}
        self.assertEqual(
            len(coordinates),
            len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        # check if total values are equal
        values = df[["Value"]].values
        self.assertEqual(
            self.total_value,
            sum(values))

    def test_execute_mdx_dataframe_pivot(self):
        mdx = MDX_TEMPLATE.format(
            rows="{{ HEAD ( {{ [{}].MEMBERS }}, 7 ) }}".format(DIMENSION_NAMES[0]),
            columns="{{ HEAD ( {{ [{}].MEMBERS }}, 8 ) }}".format(DIMENSION_NAMES[1]),
            cube="[{}]".format(CUBE_NAME),
            where="( [{}].[{}] )".format(DIMENSION_NAMES[2], "Element1")
        )
        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 8))

    def test_execute_mdx_dataframe_pivot_no_titles(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{{ HEAD ( {{ [{}].MEMBERS }}, 7 ) }}".format(DIMENSION_NAMES[0]),
            columns="{{ HEAD ( {{ [{}].MEMBERS }}, 5 ) }} * {{ HEAD ( {{ [{}].MEMBERS }}, 5 ) }}".format(
                DIMENSION_NAMES[1], DIMENSION_NAMES[2]),
            cube="[{}]".format(CUBE_NAME)
        )
        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 5 * 5))

    def test_execute_mdx_cellcount(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        cell_count = self.tm1.cubes.cells.execute_mdx_cellcount(mdx)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_rows_and_values_string_set_one_row_dimension(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[0] + ")}",
            columns="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[2] + ")}*{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[
                1] + ")}",
            cube=STRING_CUBE_NAME)
        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_two_row_dimensions(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[0] + ")}*{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[1] + ")}",
            columns="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[2] + ")}",
            cube=STRING_CUBE_NAME)
        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_include_empty(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[0] + ")}*{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[1] + ")}",
            columns="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[2] + ")}",
            cube=STRING_CUBE_NAME)
        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(
            mdx=mdx,
            exclude_empty_cells=False)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3", ""})

    def test_execute_mdx_rows_and_values_string_set_against_numeric_cells(self):
        rows = "{{ HEAD( {{ Tm1SubsetAll( {} ) }},10) }} * {{ HEAD( {{ Tm1SubsetAll( {} ) }} ,10) }}".format(
            DIMENSION_NAMES[0],
            DIMENSION_NAMES[1])
        columns = "{HEAD({Tm1SubsetAll(" + DIMENSION_NAMES[2] + ")},10)}"
        mdx = MDX_TEMPLATE_SHORT.format(
            rows=rows,
            columns=columns,
            cube=CUBE_NAME)
        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(
            mdx=mdx,
            exclude_empty_cells=False)

        self.assertEqual(
            set(elements_and_string_values),
            {'Element 1',
             'Element 2',
             'Element 3',
             'Element 4',
             'Element 5',
             'Element 6',
             'Element 7',
             'Element 8',
             'Element 9',
             'Element 10'})

    def test_execute_view_rows_and_values_string_set(self):
        mdx = MDX_TEMPLATE_SHORT.format(
            rows="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[0] + ")}",
            columns="{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[2] + ")}*{Tm1SubsetAll(" + STRING_DIMENSION_NAMES[
                1] + ")}",
            cube=STRING_CUBE_NAME)
        view_name = "some view"
        view = MDXView(cube_name=STRING_CUBE_NAME, view_name=view_name, MDX=mdx)
        self.tm1.cubes.views.create(view, private=False)

        elements_and_string_values = self.tm1.cubes.cells.execute_view_rows_and_values_string_set(
            cube_name=STRING_CUBE_NAME,
            view_name=view_name,
            private=False)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "String1", "String2", "String3"})

    def test_execute_view(self):
        data = self.tm1.cubes.cells.execute_view(cube_name=CUBE_NAME, view_name=VIEW_NAME, private=False)

        # Check if total value is the same AND coordinates are the same
        check_value = 0
        for coordinates, value in data.items():
            # grid can have null values in cells as rows and columns are populated with elements
            if value['Value']:
                # extract the element name from the element unique name
                element_names = Utils.element_names_from_element_unique_names(coordinates)
                self.assertIn(element_names, self.target_coordinates)
                check_value += value['Value']

        # Check the check-sum
        self.assertEqual(check_value, self.total_value)

        # execute view with top
        data = self.tm1.cubes.cells.execute_view(cube_name=CUBE_NAME, view_name=VIEW_NAME, private=False, top=3)
        self.assertEqual(len(data.keys()), 3)

    def test_execute_view_skip_contexts(self):
        view_name = PREFIX + "View_With_Titles"
        if not self.tm1.cubes.views.exists(cube_name=CUBE_NAME, view_name=view_name, private=False):
            view = NativeView(
                cube_name=CUBE_NAME,
                view_name=view_name,
                suppress_empty_columns=False,
                suppress_empty_rows=False)
            view.add_row(
                dimension_name=DIMENSION_NAMES[0],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[0],
                    expression='{[' + DIMENSION_NAMES[0] + '].[Element 1]}'))
            view.add_column(
                dimension_name=DIMENSION_NAMES[1],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[1],
                    expression='{[' + DIMENSION_NAMES[1] + '].[Element 1]}'))
            view.add_title(
                dimension_name=DIMENSION_NAMES[2],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[2],
                    expression='{[' + DIMENSION_NAMES[2] + '].Members}'),
                selection="Element 1")
            self.tm1.cubes.views.create(
                view=view,
                private=False)

        data = self.tm1.cubes.cells.execute_view(
            cube_name=CUBE_NAME,
            view_name=view_name,
            private=False,
            skip_contexts=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                DIMENSION_NAMES[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                DIMENSION_NAMES[1])

    def test_execute_view_rows_and_values_one_dimension_on_rows(self):
        view_name = PREFIX + "MDX_View_With_One_Dim_On_Rows"
        if not self.tm1.cubes.views.exists(cube_name=CUBE_NAME, view_name=view_name, private=False):
            rows = """
                 {{ [{dim0}].[Element1], [{dim0}].[Element2] }}
                """.format(dim0=DIMENSION_NAMES[0])

            columns = """
                 {{ [{dim1}].[Element1], [{dim1}].[Element2], [{dim1}].[Element3] }}
                """.format(dim1=DIMENSION_NAMES[1])

            mdx = MDX_TEMPLATE.format(
                rows=rows,
                columns=columns,
                cube=CUBE_NAME,
                where="[" + DIMENSION_NAMES[2] + "].[Element1]")
            view = MDXView(cube_name=CUBE_NAME, view_name=view_name, MDX=mdx)
            self.tm1.cubes.views.create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=CUBE_NAME,
            view_name=view_name,
            private=False)

        self.assertEqual(len(data), 2)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            self.assertEqual(len(cells), 3)

    def test_execute_view_rows_and_values_with_member_names(self):
        view_name = PREFIX + "MDX_View_With_Member_Names"
        if not self.tm1.cubes.views.exists(cube_name=CUBE_NAME, view_name=view_name, private=False):
            rows = """
                 {{ [{dim0}].[Element1], [{dim0}].[Element2] }} * {{ [{dim2}].[Element1], [{dim2}].[Element2] }}
                """.format(dim0=DIMENSION_NAMES[0], dim2=DIMENSION_NAMES[2])

            columns = """
                 {{ [{dim1}].[Element1], [{dim1}].[Element2], [{dim1}].[Element3] }}
                """.format(dim1=DIMENSION_NAMES[1])

            mdx = MDX_TEMPLATE.format(
                rows=rows,
                columns=columns,
                cube=CUBE_NAME,
                where="[" + DIMENSION_NAMES[2] + "].[Element1]")
            view = MDXView(cube_name=CUBE_NAME, view_name=view_name, MDX=mdx)
            self.tm1.cubes.views.create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=CUBE_NAME,
            view_name=view_name,
            private=False,
            element_unique_names=False)

        self.assertEqual(len(data), 4)
        self.assertIn(("Element1", "Element1"), data)
        self.assertIn(("Element1", "Element2"), data)
        self.assertIn(("Element2", "Element1"), data)
        self.assertIn(("Element2", "Element2"), data)
        for _, cells in data.items():
            self.assertEqual(len(cells), 3)

    def test_execute_view_rows_and_values_two_dimensions_on_rows(self):
        view_name = PREFIX + "MDX_View_With_Two_Dim_On_Rows"
        if not self.tm1.cubes.views.exists(cube_name=CUBE_NAME, view_name=view_name, private=False):
            rows = """
                {{ [{dim0}].[Element1], [{dim0}].[Element2]}} * {{ [{dim1}].[Element1], [{dim1}].[Element2] }}
                """.format(dim0=DIMENSION_NAMES[0], dim1=DIMENSION_NAMES[1])

            columns = """
                 {{ [{dim2}].[Element1], [{dim2}].[Element2], [{dim2}].[Element3] }}
                """.format(dim2=DIMENSION_NAMES[2])

            mdx = MDX_TEMPLATE.format(
                rows=rows,
                columns=columns,
                cube=CUBE_NAME,
                where="[" + DIMENSION_NAMES[2] + "].[Element1]")
            view = MDXView(cube_name=CUBE_NAME, view_name=view_name, MDX=mdx)
            self.tm1.cubes.views.create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=CUBE_NAME,
            view_name=view_name,
            private=False)

        self.assertEqual(len(data), 4)
        for row, cells in data.items():
            self.assertEqual(len(row), 2)
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            dimension = Utils.dimension_name_from_element_unique_name(row[1])
            self.assertEqual(dimension, DIMENSION_NAMES[1])
            self.assertEqual(len(cells), 3)

    def test_execute_view_raw_skip_contexts(self):
        view_name = PREFIX + "View_With_Titles"
        if not self.tm1.cubes.views.exists(cube_name=CUBE_NAME, view_name=view_name, private=False):
            view = NativeView(
                cube_name=CUBE_NAME,
                view_name=view_name,
                suppress_empty_columns=False,
                suppress_empty_rows=False)
            view.add_row(
                dimension_name=DIMENSION_NAMES[0],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[0],
                    expression='{[' + DIMENSION_NAMES[0] + '].[Element 1]}'))
            view.add_column(
                dimension_name=DIMENSION_NAMES[1],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[1],
                    expression='{[' + DIMENSION_NAMES[1] + '].[Element 1]}'))
            view.add_title(
                dimension_name=DIMENSION_NAMES[2],
                subset=AnonymousSubset(
                    dimension_name=DIMENSION_NAMES[2],
                    expression='{[' + DIMENSION_NAMES[2] + '].Members}'),
                selection="Element 1")
            self.tm1.cubes.views.create(
                view=view,
                private=False)

        raw_response = self.tm1.cubes.cells.execute_view_raw(
            cube_name=CUBE_NAME,
            view_name=view_name,
            private=False,
            skip_contexts=True,
            member_properties=["UniqueName"])

        self.assertEqual(len(raw_response["Axes"]), 2)
        for axis in raw_response["Axes"]:
            dimension_on_axis = Utils.dimension_name_from_element_unique_name(
                axis["Tuples"][0]["Members"][0]["UniqueName"])
            self.assertNotEqual(dimension_on_axis, DIMENSION_NAMES[2])

    def test_execute_view_raw_with_member_properties_without_elem_properties(self):
        # Member properties and no element properties
        raw = self.tm1.cubes.cells.execute_view_raw(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False,
            cell_properties=["Value", "RuleDerived"],
            member_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"])
        cells = raw["Cells"]
        # check if cell_property selection works
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
            self.assertNotIn("Consolidated", cell)
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    self.assertIn("Name", member)
                    self.assertIn("UniqueName", member)
                    self.assertNotIn("Type", member)
                    self.assertNotIn("Element", member)
                    self.assertIn("Attr1", member["Attributes"])
                    self.assertIn("Attr2", member["Attributes"])
                    self.assertNotIn("Attr3", member["Attributes"])
                    self.assertEqual(member["Attributes"]["Attr1"], "TM1py")
                    self.assertEqual(member["Attributes"]["Attr2"], 2)

    def test_execute_view_raw_with_elem_properties_without_member_properties(self):
        raw = self.tm1.cubes.cells.execute_view_raw(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"])
        cells = raw["Cells"]
        # check if cell_property selection works
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
            self.assertNotIn("Consolidated", cell)
        # check if elem property selection works
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    element = member["Element"]
                    self.assertIn("Name", element)
                    self.assertIn("UniqueName", element)
                    self.assertNotIn("Type", element)
                    self.assertIn("Attr1", element["Attributes"])
                    self.assertIn("Attr2", element["Attributes"])
                    self.assertNotIn("Attr3", element["Attributes"])
                    self.assertEqual(element["Attributes"]["Attr1"], "TM1py")
                    self.assertEqual(element["Attributes"]["Attr2"], 2)
                    self.assertNotIn("Type", member)
                    self.assertNotIn("UniqueName", member)
                    self.assertNotIn("Ordinal", member)

    def test_execute_view_with_elem_properties_with_member_properties(self):
        raw = self.tm1.cubes.cells.execute_view_raw(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"],
            member_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"])
        cells = raw["Cells"]
        # check if cell_property selection works
        for cell in cells:
            self.assertIn("Value", cell)
            if cell["Value"]:
                self.assertGreater(cell["Value"], 0)
                self.assertLess(cell["Value"], 1001)
            self.assertIn("RuleDerived", cell)
            self.assertFalse(cell["RuleDerived"])
            self.assertNotIn("Updateable", cell)
            self.assertNotIn("Consolidated", cell)
        # check if elem property selection works
        axes = raw["Axes"]
        for axis in axes:
            for member_tuple in axis["Tuples"]:
                for member in member_tuple["Members"]:
                    self.assertIn("Name", member)
                    self.assertIn("UniqueName", member)
                    self.assertNotIn("Type", member)
                    self.assertIn("Attr1", member["Attributes"])
                    self.assertIn("Attr2", member["Attributes"])
                    self.assertNotIn("Attr3", member["Attributes"])
                    self.assertEqual(member["Attributes"]["Attr1"], "TM1py")
                    self.assertEqual(member["Attributes"]["Attr2"], 2)
                    element = member["Element"]
                    self.assertIn("Name", element)
                    self.assertNotIn("Type", element)
                    self.assertIn("Attr1", element["Attributes"])
                    self.assertIn("Attr2", element["Attributes"])
                    self.assertNotIn("Attr3", element["Attributes"])
                    self.assertEqual(element["Attributes"]["Attr1"], "TM1py")
                    self.assertEqual(element["Attributes"]["Attr2"], 2)

    def test_execute_view_raw_with_top(self):
        # check if top works
        raw = self.tm1.cubes.cells.execute_view_raw(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"],
            top=5)
        self.assertEqual(len(raw["Cells"]), 5)

    def test_execute_view_values(self):
        cell_values = self.tm1.cubes.cells.execute_view_values(cube_name=CUBE_NAME, view_name=VIEW_NAME, private=False)

        # check type
        self.assertIsInstance(cell_values, types.GeneratorType)

        # Check if total value is the same AND coordinates are the same. Handle None.
        self.assertEqual(self.total_value,
                         sum([v for v in cell_values if v]))

    def test_execute_view_csv(self):
        csv = self.tm1.cubes.cells.execute_view_csv(cube_name=CUBE_NAME, view_name=VIEW_NAME, private=False)

        # check type
        self.assertIsInstance(csv, str)
        records = csv.split('\r\n')[1:]
        coordinates = {tuple(record.split(',')[0:3]) for record in records if record != '' and records[4] != 0}

        # check number of coordinates (with values)
        self.assertEqual(len(coordinates), len(self.target_coordinates))

        # check if coordinates are the same
        self.assertTrue(coordinates.issubset(self.target_coordinates))
        values = [float(record.split(',')[3]) for record in records if record != '']

        # check if sum of retrieved values is sum of written values
        self.assertEqual(self.total_value, sum(values))

    def test_execute_view_dataframe(self):
        df = self.tm1.cubes.cells.execute_view_dataframe(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates
        coordinates = {tuple(row)
                       for row
                       in df[[*DIMENSION_NAMES]].values}
        self.assertEqual(len(coordinates), len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        # check values
        values = df[["Value"]].values
        self.assertEqual(self.total_value, sum(values))

    def test_execute_view_dataframe_pivot_two_row_one_column_dimensions(self):
        view_name = PREFIX + "Pivot_two_row_one_column_dimensions"
        view = NativeView(
            cube_name=CUBE_NAME,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=DIMENSION_NAMES[0],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[0],
                expression='{ HEAD ( {[' + DIMENSION_NAMES[0] + '].Members}, 10) } }'))
        view.add_row(
            dimension_name=DIMENSION_NAMES[1],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[1],
                expression='{ HEAD ( { [' + DIMENSION_NAMES[1] + '].Members}, 10 ) }'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[2],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[2],
                expression='{ HEAD ( {[' + DIMENSION_NAMES[2] + '].Members}, 10 ) }'))
        self.tm1.cubes.views.create(view, private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=CUBE_NAME,
            view_name=view_name)
        self.assertEqual((100, 10), pivot.shape)

    def test_execute_view_dataframe_pivot_one_row_two_column_dimensions(self):
        view_name = PREFIX + "Pivot_one_row_two_column_dimensions"
        view = NativeView(
            cube_name=CUBE_NAME,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=DIMENSION_NAMES[0],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[0],
                expression='{ HEAD ( {[' + DIMENSION_NAMES[0] + '].Members}, 10) } }'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[1],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[1],
                expression='{ HEAD ( { [' + DIMENSION_NAMES[1] + '].Members}, 10 ) }'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[2],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[2],
                expression='{ HEAD ( {[' + DIMENSION_NAMES[2] + '].Members}, 10 ) }'))
        self.tm1.cubes.views.create(
            view=view,
            private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=CUBE_NAME,
            view_name=view_name)
        self.assertEqual((10, 100), pivot.shape)

    def test_execute_view_dataframe_pivot_one_row_one_column_dimensions(self):
        view_name = PREFIX + "Pivot_one_row_one_column_dimensions"
        view = NativeView(
            cube_name=CUBE_NAME,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=DIMENSION_NAMES[0],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[0],
                expression='{ HEAD ( {[' + DIMENSION_NAMES[0] + '].Members}, 10) } }'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[1],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[1],
                expression='{ HEAD ( { [' + DIMENSION_NAMES[1] + '].Members}, 10 ) }'))
        view.add_title(
            dimension_name=DIMENSION_NAMES[2],
            selection="Element 1",
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[2],
                elements=("Element 1",)))
        self.tm1.cubes.views.create(view, private=False)
        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=CUBE_NAME,
            view_name=view_name)
        self.assertEqual((10, 10), pivot.shape)

    def test_execute_mdxview_dataframe_pivot(self):
        mdx = MDX_TEMPLATE.format(
            rows="{{ [{}].DefaultMember }}".format(DIMENSION_NAMES[0]),
            columns="{{ [{}].DefaultMember }}".format(DIMENSION_NAMES[1]),
            cube="[{}]".format(CUBE_NAME),
            where="( [{}].[{}] )".format(DIMENSION_NAMES[2], "Element1")
        )
        view = MDXView(CUBE_NAME, PREFIX + "MDX_VIEW", mdx)
        self.tm1.cubes.views.create(
            view=view,
            private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=CUBE_NAME,
            view_name=view.name,
            private=False)
        self.assertEqual((1, 1), pivot.shape)

        self.tm1.cubes.views.delete(
            cube_name=CUBE_NAME,
            view_name=view.name,
            private=False)

    def test_execute_view_cellcount(self):
        cell_count = self.tm1.cubes.cells.execute_view_cellcount(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_ui_array(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        self.tm1.cubes.cells.execute_mdx_ui_array(mdx=mdx)

    def test_execute_view_ui_array(self):
        self.tm1.cubes.cells.execute_view_ui_array(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

    def test_execute_mdx_ui_dygraph(self):
        mdx = """
        SELECT
        NON EMPTY [{}].MEMBERS * [{}].MEMBERS ON ROWS,
        NON EMPTY [{}].MEMBERS ON COLUMNS
        FROM [{}]
        """.format(*DIMENSION_NAMES, CUBE_NAME)
        self.tm1.cubes.cells.execute_mdx_ui_dygraph(mdx=mdx)

    def test_execute_view_ui_dygraph(self):
        self.tm1.cubes.cells.execute_view_ui_dygraph(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

    def test_write_values_through_cellset(self):
        mdx_skeleton = "SELECT {} " \
                       "ON ROWS, {} " \
                       "ON COLUMNS " \
                       "FROM {} " \
                       "WHERE ({})"
        mdx = mdx_skeleton.format(
            "{{[{}].[{}]}}".format(DIMENSION_NAMES[0], "element2"),
            "{{[{}].[{}]}}".format(DIMENSION_NAMES[1], "element2"),
            CUBE_NAME,
            "[{}].[{}]".format(DIMENSION_NAMES[2], "element2"))

        original_value = next(self.tm1.cubes.cells.execute_mdx_values(mdx))

        self.tm1.cubes.cells.write_values_through_cellset(mdx, (1.5,))

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(next(values), 1.5)

        self.tm1.cubes.cells.write_values_through_cellset(mdx, (original_value,))

    def test_deactivate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="YES",
                                         cube_name="}CubeProperties",
                                         element_tuple=(CUBE_NAME, "Logging"))
        self.tm1.cubes.cells.deactivate_transactionlog(CUBE_NAME)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(CUBE_NAME))
        self.assertEqual("NO", value.upper())

    def test_activate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="NO",
                                         cube_name="}CubeProperties",
                                         element_tuple=(CUBE_NAME, "Logging"))
        self.tm1.cubes.cells.activate_transactionlog(CUBE_NAME)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(CUBE_NAME))
        self.assertEqual("YES", value.upper())

    def test_read_write_with_custom_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(STRING_CUBE_NAME, {coordinates: LATIN_1_ENCODED_TEXT}, encoding="latin-1")

        mdx = f"""
        SELECT
        {"*".join(
            "{[" + dimension + "].[" + element + "]}"
            for dimension, element
            in zip(STRING_DIMENSION_NAMES, coordinates))} ON 0
        FROM
        [{STRING_CUBE_NAME}]
        """

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertEqual(LATIN_1_ENCODED_TEXT, next(values))

    def test_read_write_with_custom_encoding_fail_response_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(STRING_CUBE_NAME, {coordinates: LATIN_1_ENCODED_TEXT}, encoding="latin-1")

        mdx = f"""
        SELECT
        {"*".join(
            "{[" + dimension + "].[" + element + "]}"
            for dimension, element
            in zip(STRING_DIMENSION_NAMES, coordinates))} ON 0
        FROM
        [{STRING_CUBE_NAME}]
        """
        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx)

        self.assertNotEqual(LATIN_1_ENCODED_TEXT, next(values))

    def test_read_write_with_custom_encoding_fail_request_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(STRING_CUBE_NAME, {coordinates: LATIN_1_ENCODED_TEXT})

        mdx = f"""
        SELECT
        {"*".join(
            "{[" + dimension + "].[" + element + "]}"
            for dimension, element
            in zip(STRING_DIMENSION_NAMES, coordinates))} ON 0
        FROM
        [{STRING_CUBE_NAME}]
        """
        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertNotEqual(LATIN_1_ENCODED_TEXT, next(values))

    def test_clear_with_mdx_happy_case(self):
        cells = {("Element1", "Element1", "Element1"): 1}
        self.tm1.cells.write_values(CUBE_NAME, cells)

        mdx = f"""
        SELECT
        {{[{DIMENSION_NAMES[0]}].[Element1]}} ON 0,
        {{[{DIMENSION_NAMES[1]}].[Element1]}} ON 1
        FROM [{CUBE_NAME}]
        WHERE ([{DIMENSION_NAMES[2]}].[Element1])
        """
        self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        value = next(self.tm1.cells.execute_mdx_values(mdx=mdx))
        self.assertEqual(value, None)

    def test_clear_with_mdx_all_on_axis0(self):
        cells = {("Element1", "Element1", "Element1"): 1}
        self.tm1.cells.write_values(CUBE_NAME, cells)

        mdx = f"""
        SELECT
        {{[{DIMENSION_NAMES[0]}].[Element1]}}*{{[{DIMENSION_NAMES[1]}].[Element1]}}*{{[{DIMENSION_NAMES[2]}].[Element1]}} ON 0
        FROM [{CUBE_NAME}]
        """
        self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        value = next(self.tm1.cells.execute_mdx_values(mdx=mdx))
        self.assertEqual(value, None)

    def test_clear_with_mdx_invalid_query(self):
        with pytest.raises(TM1pyException) as execinfo:
            mdx = f"""
            SELECT
            {{[{DIMENSION_NAMES[0]}].[NotExistingElement]}} ON 0
            FROM [{CUBE_NAME}]
            """
            self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        self.assertEqual(
            f"Failed to clear cube: '{CUBE_NAME}' with mdx: '{abbreviate_mdx(mdx, 100)}'",
            execinfo.value.message)

    # Delete Cube and Dimensions
    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(CUBE_NAME)
        for dimension_name in DIMENSION_NAMES:
            cls.tm1.dimensions.delete(dimension_name)
        cls.remove_assets_for_relative_proportional_spread_tests()
        cls.remove_string_cube()
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
