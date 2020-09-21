import configparser
import unittest
from pathlib import Path

from mdxpy import CalculatedMember, MdxBuilder, MdxHierarchySet, Member

from TM1py.Exceptions.Exceptions import TM1pyException, TM1pyVersionException
from TM1py.Objects import (AnonymousSubset, Cube, Dimension, Element,
                           ElementAttribute, Hierarchy, MDXView, NativeView)
from TM1py.Services import TM1Service
from TM1py.Utils import Utils, element_names_from_element_unique_names, CaseAndSpaceInsensitiveDict
from .TestUtils import skip_if_insufficient_version, skip_if_no_pandas

try:
    import pandas as pd
except ImportError:
    pass

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

CUBE_RPS1_NAME = PREFIX + "Cube" + "_RPS1"
CUBE_RPS2_NAME = PREFIX + "Cube" + "_RPS2"

CUBE_WITH_CONSOLIDATIONS_NAME = CUBE_NAME + "_With_Consolidations"
DIMENSIONS_WITH_CONSOLIDATIONS_NAMES = [dimension_name + "_With_Consolidations" for dimension_name in DIMENSION_NAMES]
CUBE_WITH_RULES_NAME = CUBE_NAME + "_With_Rules"

DIMENSION_RPS1_NAME = PREFIX + "Dimension" + "_RPS1"
DIMENSION_RPS2_NAME = PREFIX + "Dimension" + "_RPS2"


class TestCellMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

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
            attribute_values = {}
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
        value = 1
        for element1, element2, element3 in cls.target_coordinates:
            cls.cellset[(element1, element2, element3)] = value

        # Sum of all the values that we write in the cube. serves as a checksum.
        cls.total_value = sum(cls.cellset.values())

        # Fill cube with values
        cls.tm1.cubes.cells.write_values(CUBE_NAME, cls.cellset)

        # For tests on string related methods
        cls.build_string_cube()

        cls.build_cube_with_rules()

        cls.build_cube_with_consolidations()

    @classmethod
    def setup(cls):
        # set correct version before test, as it is overwritten in a test case
        cls.tm1._tm1_rest.set_version()

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
    def build_cube_with_rules(cls):
        cube = Cube(name=CUBE_WITH_RULES_NAME, dimensions=DIMENSION_NAMES)
        cube.rules = f"['{DIMENSION_NAMES[0]}':'Element1'] = N: 1;\r\n"
        cls.tm1.cubes.create(cube)

    @classmethod
    def remove_cube_with_rules(cls):
        cls.tm1.cubes.delete(CUBE_WITH_RULES_NAME)

    @classmethod
    def build_cube_with_consolidations(cls):
        for dimension_name_source, dimension_name_target in zip(DIMENSION_NAMES, DIMENSIONS_WITH_CONSOLIDATIONS_NAMES):
            dimension = cls.tm1.dimensions.get(dimension_name=dimension_name_source)
            dimension.name = dimension_name_target
            hierarchy = dimension.get_hierarchy(dimension_name_target)
            for element in hierarchy:
                hierarchy.add_edge(parent="TOTAL_" + dimension_name_target, component=element.name, weight=1)
            hierarchy.add_element("TOTAL_" + dimension_name_target, "Consolidated")
            cls.tm1.dimensions.create(dimension)

        cube = Cube(name=CUBE_WITH_CONSOLIDATIONS_NAME, dimensions=DIMENSIONS_WITH_CONSOLIDATIONS_NAMES)
        cls.tm1.cubes.create(cube)

    @classmethod
    def remove_cube_with_consolidations(cls):
        if cls.tm1.cubes.exists(cube_name=CUBE_WITH_CONSOLIDATIONS_NAME):
            cls.tm1.cubes.delete(cube_name=CUBE_WITH_CONSOLIDATIONS_NAME)
        for dimension_name in DIMENSIONS_WITH_CONSOLIDATIONS_NAMES:
            if cls.tm1.dimensions.exists(dimension_name=dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def build_assets_for_relative_proportional_spread_tests(cls):
        for dimension_name in (DIMENSION_RPS1_NAME, DIMENSION_RPS2_NAME):
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

        for cube_name in (CUBE_RPS1_NAME, CUBE_RPS2_NAME):
            cube = Cube(name=cube_name, dimensions=(DIMENSION_RPS1_NAME, DIMENSION_RPS2_NAME))
            if not cls.tm1.cubes.exists(cube.name):
                cls.tm1.cubes.create(cube)
            # zero out cube
            cls.tm1.processes.execute_ti_code("CubeClearData('" + cube_name + "');")

    @classmethod
    def remove_assets_for_relative_proportional_spread_tests(cls):
        for cube_name in (CUBE_RPS1_NAME, CUBE_RPS2_NAME):
            if cls.tm1.cubes.exists(cube_name):
                cls.tm1.cubes.delete(cube_name=cube_name)
        for dimension_name in (DIMENSION_RPS1_NAME, DIMENSION_RPS2_NAME):
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
        cells = dict()
        cells["Element 2", "Element4", "Element7"] = 716

        self.tm1.cubes.cells.write_values(CUBE_NAME, cells)
        query = MdxBuilder.from_cube(CUBE_NAME)
        query.add_member_tuple_to_columns(
            f"[{DIMENSION_NAMES[0]}].[Element 2]",
            f"[{DIMENSION_NAMES[1]}].[Element 4]",
            f"[{DIMENSION_NAMES[2]}].[Element 7]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [716])

    def test_write(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 717
        self.tm1.cubes.cells.write(CUBE_NAME, cells)

        query = MdxBuilder.from_cube(CUBE_NAME)
        query.add_member_tuple_to_columns(
            f"[{DIMENSION_NAMES[0]}].[Element 1]",
            f"[{DIMENSION_NAMES[1]}].[Element 4]",
            f"[{DIMENSION_NAMES[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [717])

    def test_write_increment_true(self):
        cells = dict()
        cells["Element 1", "Element5", "Element8"] = 211

        self.tm1.cubes.cells.write(CUBE_NAME, cells)
        self.tm1.cubes.cells.write(CUBE_NAME, cells, increment=True)

        query = MdxBuilder.from_cube(CUBE_NAME)
        query.add_member_tuple_to_columns(
            f"[{DIMENSION_NAMES[0]}].[Element 1]",
            f"[{DIMENSION_NAMES[1]}].[Element 5]",
            f"[{DIMENSION_NAMES[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [422])

    def test_write_increment_false(self):
        cells = dict()
        cells["Element 1", "Element5", "Element8"] = 211

        self.tm1.cubes.cells.write(CUBE_NAME, cells)
        self.tm1.cubes.cells.write(CUBE_NAME, cells, increment=False)

        query = MdxBuilder.from_cube(CUBE_NAME)
        query.add_member_tuple_to_columns(
            f"[{DIMENSION_NAMES[0]}].[Element 1]",
            f"[{DIMENSION_NAMES[1]}].[Element 5]",
            f"[{DIMENSION_NAMES[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [211])

    @skip_if_no_pandas
    def test_write_dataframe(self):
        df = pd.DataFrame({
            DIMENSION_NAMES[0]: ["element 1", "element 1", "element 1"],
            DIMENSION_NAMES[1]: ["element 1", "element 2", "element 3"],
            DIMENSION_NAMES[2]: ["element 5", "element 5", "element 5"],
            "Value": [1, 2, 3]})
        self.tm1.cubes.cells.write_dataframe(CUBE_NAME, df)

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "element 1"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[1], "element 1"),
            Member.of(DIMENSION_NAMES[1], "element 2"),
            Member.of(DIMENSION_NAMES[1], "element 3")])) \
            .add_member_to_where(Member.of(DIMENSION_NAMES[2], "element 5")).to_mdx()
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)

        self.assertEqual(list(df["Value"]), values)

    @skip_if_no_pandas
    def test_write_dataframe_error(self):
        df = pd.DataFrame({
            DIMENSION_NAMES[0]: ["element 1", "element 3", "element 5"],
            DIMENSION_NAMES[1]: ["element 1", "element 2", "element 4"],
            DIMENSION_NAMES[2]: ["element 1", "element 3", "element 5"],
            "Extra Column": ["element 1", "element2", "element3"],
            "Value": [1, 2, 3]})
        with self.assertRaises(ValueError) as e:
            self.tm1.cubes.cells.write_dataframe(CUBE_NAME, df)

    def test_relative_proportional_spread_happy_case(self):
        """
        Tests that relative proportional spread populates a cube with the expected values
        """
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_RPS1_NAME, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_RPS1_NAME,
            unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[e2]", "[" + DIMENSION_RPS2_NAME + "].[c1]"),
            reference_cube=CUBE_RPS1_NAME,
            reference_unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[c1]", "[" + DIMENSION_RPS2_NAME + "].[c1]"))

        mdx = MdxBuilder.from_cube(CUBE_RPS1_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_RPS1_NAME, "e2"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_RPS2_NAME, "e1"),
            Member.of(DIMENSION_RPS2_NAME, "e2"),
            Member.of(DIMENSION_RPS2_NAME, "e3")])).to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx)

        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_with_explicit_hierarchies(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_RPS1_NAME, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_RPS1_NAME,
            unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[" + DIMENSION_RPS1_NAME + "].[e2]",
                                  "[" + DIMENSION_RPS2_NAME + "].[" + DIMENSION_RPS2_NAME + "].[c1]"),
            reference_cube=CUBE_RPS1_NAME,
            reference_unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[" + DIMENSION_RPS1_NAME + "].[c1]",
                                            "[" + DIMENSION_RPS2_NAME + "].[" + DIMENSION_RPS2_NAME + "].[c1]"))

        mdx = MdxBuilder.from_cube(CUBE_RPS1_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_RPS1_NAME, "e2"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_RPS2_NAME, "e1"),
            Member.of(DIMENSION_RPS2_NAME, "e2"),
            Member.of(DIMENSION_RPS2_NAME, "e3")])).to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_spread_without_reference_cube(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_RPS1_NAME, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_RPS1_NAME,
            unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[e2]", "[" + DIMENSION_RPS2_NAME + "].[c1]"),
            reference_unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[c1]", "[" + DIMENSION_RPS2_NAME + "].[c1]"))

        mdx = MdxBuilder.from_cube(CUBE_RPS1_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_RPS1_NAME, "e2"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_RPS2_NAME, "e1"),
            Member.of(DIMENSION_RPS2_NAME, "e2"),
            Member.of(DIMENSION_RPS2_NAME, "e3")])).to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_spread_with_different_reference_cube(self):
        self.build_assets_for_relative_proportional_spread_tests()

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(CUBE_RPS2_NAME, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=CUBE_RPS1_NAME,
            unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[e2]", "[" + DIMENSION_RPS2_NAME + "].[c1]"),
            reference_cube=CUBE_RPS2_NAME,
            reference_unique_element_names=("[" + DIMENSION_RPS1_NAME + "].[c1]", "[" + DIMENSION_RPS2_NAME + "].[c1]"))

        mdx = MdxBuilder.from_cube(CUBE_RPS1_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_RPS1_NAME, "e2"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_RPS2_NAME, "e1"),
            Member.of(DIMENSION_RPS2_NAME, "e2"),
            Member.of(DIMENSION_RPS2_NAME, "e3")])).to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_execute_mdx(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(
            self.total_value, sum(v["Value"] for v in data.values() if v["Value"])
        )

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
        self.assertEqual(sum(range(1000)), sum(v["Ordinal"] for v in data.values()))

    def test_execute_mdx_without_rows(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.from_str("", "", "{}")) \
            .to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(
            self.total_value, sum(v["Value"] for v in data.values() if v["Value"])
        )

        for coordinates in data.keys():
            self.assertEqual(len(coordinates), 3)
            self.assertIn("[TM1py_Tests_Cell_Dimension1].", coordinates[0])
            self.assertIn("[TM1py_Tests_Cell_Dimension2].", coordinates[1])
            self.assertIn("[TM1py_Tests_Cell_Dimension3].", coordinates[2])

    def test_execute_mdx_without_columns(self):
        # write cube content
        self.tm1.cubes.cells.write_values(CUBE_NAME, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty().add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .columns_non_empty().add_hierarchy_set_to_column_axis(MdxHierarchySet.from_str("", "", "{}")) \
            .to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(
            self.total_value, sum(v["Value"] for v in data.values() if v["Value"])
        )

        for coordinates in data.keys():
            self.assertEqual(len(coordinates), 3)
            self.assertIn("[TM1py_Tests_Cell_Dimension1].", coordinates[0])
            self.assertIn("[TM1py_Tests_Cell_Dimension2].", coordinates[1])
            self.assertIn("[TM1py_Tests_Cell_Dimension3].", coordinates[2])

    def test_execute_mdx_skip_contexts(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

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

    def test_execute_mdx_skip_consolidated(self):
        mdx = MdxBuilder.from_cube(CUBE_WITH_CONSOLIDATIONS_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[0], "Total_" + DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[0]),
            Member.of(DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[0], "Element1")])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_contexts=True, skip_consolidated_cells=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                DIMENSIONS_WITH_CONSOLIDATIONS_NAMES[1])

    def test_execute_mdx_skip_rule_derived(self):
        mdx = MdxBuilder.from_cube(CUBE_WITH_RULES_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[0], "Element 1"),
            Member.of(DIMENSION_NAMES[0], "Element 2")])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_contexts=True, skip_rule_derived_cells=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                DIMENSION_NAMES[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                DIMENSION_NAMES[1])

    def test_execute_mdx_skip_zeros(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[0], "Element 1"),
            Member.of(DIMENSION_NAMES[0], "Element 2")])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_contexts=False, skip_zeros=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 3)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                DIMENSION_NAMES[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                DIMENSION_NAMES[1])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[2]),
                DIMENSION_NAMES[2])

    def test_execute_mdx_raw_skip_contexts(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_axis(1, MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element1"))) \
            .add_hierarchy_set_to_axis(0, MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            self.assertEqual(len(cells), 1)

    def test_execute_mdx_rows_and_values_empty_cellset(self):
        # make sure it's empty
        self.tm1.cubes.cells.write_values(CUBE_NAME, {("Element10", "Element11", "Element13"): 0})

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element10"))) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element11"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element13]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)
        self.assertEqual(len(data), 0)

    def test_execute_mdx_rows_and_values_member_names(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element1"))) \
            .add_member_to_where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=False)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            member_name = row[0]
            self.assertEqual(member_name, "Element 1")

    def test_execute_mdx_rows_and_values_one_dimension_on_rows(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[0], "Element1"),
            Member.of(DIMENSION_NAMES[0], "Element2")])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[1], "Element1"),
            Member.of(DIMENSION_NAMES[1], "Element2"),
            Member.of(DIMENSION_NAMES[1], "Element3")])) \
            .where("[" + DIMENSION_NAMES[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx)

        self.assertEqual(len(data), 2)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, DIMENSION_NAMES[0])
            self.assertEqual(len(cells), 3)

    def test_execute_mdx_rows_and_values_two_dimensions_on_rows(self):

        mdx = MdxBuilder.from_cube(CUBE_NAME).add_hierarchy_set_to_axis(0, MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[2], "Element1"),
            Member.of(DIMENSION_NAMES[2], "Element2"),
            Member.of(DIMENSION_NAMES[2], "Element3")])) \
            .add_hierarchy_set_to_axis(1, MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[0], "Element1"),
            Member.of(DIMENSION_NAMES[0], "Element2")])). \
            add_hierarchy_set_to_axis(1, MdxHierarchySet.members([
            Member.of(DIMENSION_NAMES[1], "Element1"),
            Member.of(DIMENSION_NAMES[1], "Element2")])).to_mdx()

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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

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

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        cell_values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertIsInstance(
            cell_values,
            list)
        # Check if total value is the same. Handle None.
        self.assertEqual(self.total_value, sum(v for v in cell_values if v))
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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(DIMENSION_NAMES + ["Value"]),
            header)

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

    def test_execute_mdx_csv_empty_cellset(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element9"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element 18"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[2], "Element 2"))) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        self.assertEqual("", csv)

    def test_execute_mdx_csv_skip_rule_derived(self):
        mdx = MdxBuilder.from_cube(CUBE_WITH_RULES_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(100)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2]).head(100)) \
            .add_member_to_where(Member.of(DIMENSION_NAMES[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, skip_rule_derived_cells=True)

        self.assertEqual("", csv)

    def test_execute_mdx_csv_top(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2]).head(10)) \
            .add_member_to_where(Member.of(DIMENSION_NAMES[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, top=10, skip_zeros=False)

        records = csv.split("\r\n")
        self.assertEqual(11, len(records))

    def test_execute_mdx_csv_skip(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2]).head(10)) \
            .add_member_to_where(Member.of(DIMENSION_NAMES[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, skip=10, skip_zeros=False)

        records = csv.split("\r\n")
        self.assertEqual(91, len(records))

    def test_execute_mdx_csv_with_calculated_member(self):
        # MDX Query with calculated MEMBER
        mdx = MdxBuilder.from_cube(CUBE_NAME).with_member(CalculatedMember.lookup_attribute(
            DIMENSION_NAMES[1],
            DIMENSION_NAMES[1],
            "Calculated Member",
            DIMENSION_NAMES[0],
            "Attr3")) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Calculated Member"))) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(DIMENSION_NAMES[0:2] + ["Value"]),
            header)

        # check coordinates
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

    def test_execute_mdx_elements_value_dict(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_elements_value_dict(mdx)

        # check type
        self.assertIsInstance(values, CaseAndSpaceInsensitiveDict)

        # check coordinates
        coordinates = {key for key, value in values.items()}
        self.assertEqual(len(coordinates), len(self.target_coordinates))

        # check values
        values = [float(value) for _, value in values.items()]
        self.assertEqual(self.total_value, sum(values))

    @skip_if_no_pandas
    def test_execute_mdx_dataframe(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

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

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_pivot(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0]).head(7)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(8)) \
            .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
            .to_mdx()

        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 8))

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_pivot_no_titles(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0]).head(7)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(5)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2]).head(5)) \
            .to_mdx()

        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 5 * 5))

    def test_execute_mdx_cellcount(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        cell_count = self.tm1.cubes.cells.execute_mdx_cellcount(mdx)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_rows_and_values_string_set_one_row_dimension(self):
        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_two_row_dimensions(self):
        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_include_empty(self):
        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(
            mdx=mdx,
            exclude_empty_cells=False)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3", ""})

    def test_execute_mdx_rows_and_values_string_set_against_numeric_cells(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0]).head(10)) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2]).head(10)) \
            .to_mdx()

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
        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[2])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(STRING_DIMENSION_NAMES[1])) \
            .to_mdx()

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
            mdx = MdxBuilder.from_cube(CUBE_NAME).add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[0], "Element1"),
                Member.of(DIMENSION_NAMES[0], "Element2")])) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[1], "Element1"),
                Member.of(DIMENSION_NAMES[1], "Element2"),
                Member.of(DIMENSION_NAMES[1], "Element3")])) \
                .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
                .to_mdx()

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
            mdx = MdxBuilder.from_cube(CUBE_NAME).add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[0], "Element1"),
                Member.of(DIMENSION_NAMES[0], "Element2")])) \
                .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[2], "Element1"),
                Member.of(DIMENSION_NAMES[2], "Element2")])) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[1], "Element1"),
                Member.of(DIMENSION_NAMES[1], "Element2"),
                Member.of(DIMENSION_NAMES[1], "Element3")])) \
                .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
                .to_mdx()

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
            mdx = MdxBuilder.from_cube(CUBE_NAME).add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[0], "Element1"),
                Member.of(DIMENSION_NAMES[0], "Element2")])) \
                .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[1], "Element1"),
                Member.of(DIMENSION_NAMES[1], "Element2")])) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(DIMENSION_NAMES[2], "Element1"),
                Member.of(DIMENSION_NAMES[2], "Element2"),
                Member.of(DIMENSION_NAMES[2], "Element3")])) \
                .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
                .to_mdx()

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
        self.assertIsInstance(cell_values, list)

        # Check if total value is the same AND coordinates are the same. Handle None.
        self.assertEqual(self.total_value, sum(v for v in cell_values if v))

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

    def test_execute_view_elements_value_dict(self):
        values = self.tm1.cubes.cells.execute_view_elements_value_dict(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

        # check type
        self.assertIsInstance(values, CaseAndSpaceInsensitiveDict)

        # check coordinates
        coordinates = {key for key, value in values.items()}
        self.assertEqual(len(coordinates), len(self.target_coordinates))

        # check values
        values = [float(value) for _, value in values.items()]
        self.assertEqual(self.total_value, sum(values))

    def test_execute_view_elements_value_dict_with_top_argument(self):
        values = self.tm1.cubes.cells.execute_view_elements_value_dict(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            top=4,
            private=False)

        # check row count
        self.assertTrue(len(values) == 4)

        # check type
        self.assertIsInstance(values, CaseAndSpaceInsensitiveDict)

    @skip_if_no_pandas
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

    @skip_if_no_pandas
    def test_execute_view_dataframe_with_top_argument(self):
        df = self.tm1.cubes.cells.execute_view_dataframe(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            top=2,
            private=False)

        # check row count
        self.assertTrue(len(df) == 2)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

    @skip_if_no_pandas
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

    @skip_if_no_pandas
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

    @skip_if_no_pandas
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

    @skip_if_no_pandas
    def test_execute_mdxview_dataframe_pivot(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.default_member(DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.default_member(DIMENSION_NAMES[1])) \
            .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
            .to_mdx()

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
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        self.tm1.cubes.cells.execute_mdx_ui_array(mdx=mdx)

    def test_execute_view_ui_array(self):
        self.tm1.cubes.cells.execute_view_ui_array(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

    def test_execute_mdx_ui_dygraph(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[0], DIMENSION_NAMES[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[1], DIMENSION_NAMES[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.all_members(DIMENSION_NAMES[2], DIMENSION_NAMES[2])) \
            .to_mdx()

        self.tm1.cubes.cells.execute_mdx_ui_dygraph(mdx=mdx)

    def test_execute_view_ui_dygraph(self):
        self.tm1.cubes.cells.execute_view_ui_dygraph(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

    def test_write_values_through_cellset(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "element2"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "element2"))) \
            .where(Member.of(DIMENSION_NAMES[2], "element2")) \
            .to_mdx()

        original_value = self.tm1.cubes.cells.execute_mdx_values(mdx)[0]

        self.tm1.cubes.cells.write_values_through_cellset(mdx, (1.5,))

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(values[0], 1.5)

    def test_write_values_through_cellset_deactivate_transaction_log(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "element2"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "element2"))) \
            .where(Member.of(DIMENSION_NAMES[2], "element2")) \
            .to_mdx()

        original_value = self.tm1.cubes.cells.execute_mdx_values(mdx)[0]

        self.tm1.cubes.cells.write_values_through_cellset(mdx, (1.5,), deactivate_transaction_log=True)

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)

        self.assertEqual(values[0], 1.5)
        self.assertFalse(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    def test_write_values_through_cellset_deactivate_transaction_log_reactivate_transaction_log(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "element2"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "element2"))) \
            .where(Member.of(DIMENSION_NAMES[2], "element2")) \
            .to_mdx()

        original_value = self.tm1.cubes.cells.execute_mdx_values(mdx)[0]

        self.tm1.cubes.cells.write_values_through_cellset(
            mdx,
            (1.5,),
            deactivate_transaction_log=True,
            reactivate_transaction_log=True)

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)

        self.assertEqual(values[0], 1.5)
        self.assertTrue(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

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

        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertEqual(LATIN_1_ENCODED_TEXT, values[0])

    def test_read_write_with_custom_encoding_fail_response_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(STRING_CUBE_NAME, {coordinates: LATIN_1_ENCODED_TEXT}, encoding="latin-1")

        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx)

        self.assertNotEqual(LATIN_1_ENCODED_TEXT, values[0])

    def test_read_write_with_custom_encoding_fail_request_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(STRING_CUBE_NAME, {coordinates: LATIN_1_ENCODED_TEXT})

        mdx = MdxBuilder.from_cube(STRING_CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(STRING_DIMENSION_NAMES[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertNotEqual(LATIN_1_ENCODED_TEXT, values[0])

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_happy_case(self):
        cells = {("Element17", "Element21", "Element15"): 1}
        self.tm1.cells.write_values(CUBE_NAME, cells)

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element17"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element21"))) \
            .where(Member.of(DIMENSION_NAMES[2], "Element15")) \
            .to_mdx()

        self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_all_on_axis0(self):
        cells = {("Element19", "Element11", "Element31"): 1}
        self.tm1.cells.write_values(CUBE_NAME, cells)

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element19"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element11"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[2], "Element31"))) \
            .to_mdx()
        self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_happy_case(self):
        cells = {("Element12", "Element17", "Element32"): 1}
        self.tm1.cells.write_values(CUBE_NAME, cells)

        kwargs = {
            DIMENSION_NAMES[0]: f"[{DIMENSION_NAMES[0]}].[Element12]",
            DIMENSION_NAMES[1]: f"{{[{DIMENSION_NAMES[1]}].[Element17]}}",
            DIMENSION_NAMES[2]: f"[{DIMENSION_NAMES[2]}].[Element32]"
        }
        self.tm1.cells.clear(cube=CUBE_NAME, **kwargs)

        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element12"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element17"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[2], "Element32"))) \
            .to_mdx()

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_invalid_element_name(self):

        with self.assertRaises(TM1pyException) as e:
            kwargs = {
                DIMENSION_NAMES[0]: f"[{DIMENSION_NAMES[0]}].[Element12]",
                DIMENSION_NAMES[1]: f"[{DIMENSION_NAMES[1]}].[Element17]",
                DIMENSION_NAMES[2]: f"[{DIMENSION_NAMES[2]}].[NotExistingElement]"
            }
            self.tm1.cells.clear(cube=CUBE_NAME, **kwargs)

        self.assertEqual(
            "{\"error\":{\"code\":\"248\",\"message\":\"\\\"NotExistingElement\\\" : member not found (rte 81)\"}}",
            str(e.exception.message))

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_invalid_query(self):
        with self.assertRaises(TM1pyException) as e:
            mdx = f"""
            SELECT
            {{[{DIMENSION_NAMES[0]}].[NotExistingElement]}} ON 0
            FROM [{CUBE_NAME}]
            """
            self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        self.assertEqual(
            "{\"error\":{\"code\":\"248\",\"message\":\"\\\"NotExistingElement\\\" : member not found (rte 81)\"}}",
            str(e.exception.message))

    def test_clear_with_mdx_unsupported_version(self):

        with self.assertRaises(TM1pyVersionException) as e:
            mdx = MdxBuilder.from_cube(CUBE_NAME) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[0], "Element19"))) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[1], "Element11"))) \
                .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(DIMENSION_NAMES[2], "Element31"))) \
                .to_mdx()

            # This needs to be rethought as may influence other tests
            self.tm1._tm1_rest._version = "11.2.00000.27"

            self.tm1.cells.clear_with_mdx(cube=CUBE_NAME, mdx=mdx)

        self.assertEqual(
            str(e.exception),
            str(TM1pyVersionException(function="clear_with_mdx", required_version="11.7")))

    def test_execute_mdx_with_skip(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(DIMENSION_NAMES[0]).head(2)) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(DIMENSION_NAMES[1]).head(2)) \
            .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
            .to_mdx()

        cells = self.tm1.cubes.cells.execute_mdx(mdx=mdx, skip=2)
        self.assertEqual(len(cells), 2)

        elements = element_names_from_element_unique_names(list(cells.keys())[0])
        self.assertEqual(elements, ("Element 2", "Element 1", "Element 1"))

        elements = element_names_from_element_unique_names(list(cells.keys())[1])
        self.assertEqual(elements, ("Element 2", "Element 2", "Element 1"))

    def test_execute_mdx_with_top_skip(self):
        mdx = MdxBuilder.from_cube(CUBE_NAME) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(DIMENSION_NAMES[0]).head(2)) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(DIMENSION_NAMES[1]).head(2)) \
            .where(Member.of(DIMENSION_NAMES[2], "Element1")) \
            .to_mdx()

        cells = self.tm1.cubes.cells.execute_mdx(mdx=mdx, top=1, skip=2)
        self.assertEqual(len(cells), 1)

        elements = element_names_from_element_unique_names(list(cells.keys())[0])
        self.assertEqual(elements, ("Element 2", "Element 1", "Element 1"))

    def test_transaction_log_is_active_false(self):
        self.tm1.cells.deactivate_transactionlog(CUBE_NAME)

        self.assertFalse(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    def test_transaction_log_is_active_true(self):
        self.tm1.cells.activate_transactionlog(CUBE_NAME)

        self.assertTrue(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    def test_manage_transaction_log_deactivate_reactivate(self):
        self.tm1.cubes.cells.write_values(
            CUBE_NAME,
            self.cellset,
            deactivate_transaction_log=True,
            reactivate_transaction_log=True)

        self.assertTrue(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    def test_manage_transaction_log_not_deactivate_not_reactivate(self):
        pre_state = self.tm1.cells.transaction_log_is_active(CUBE_NAME)

        self.tm1.cubes.cells.write_values(
            CUBE_NAME,
            self.cellset,
            deactivate_transaction_log=False,
            reactivate_transaction_log=False)

        self.assertEqual(pre_state, self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    def test_manage_transaction_log_deactivate_not_reactivate(self):
        self.tm1.cubes.cells.write_values(
            CUBE_NAME,
            self.cellset,
            deactivate_transaction_log=True,
            reactivate_transaction_log=False)

        self.assertFalse(self.tm1.cells.transaction_log_is_active(CUBE_NAME))

    # Delete Cube and Dimensions
    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(CUBE_NAME)
        cls.remove_string_cube()
        cls.remove_cube_with_rules()
        cls.remove_cube_with_consolidations()
        for dimension_name in DIMENSION_NAMES:
            cls.tm1.dimensions.delete(dimension_name)
        cls.remove_assets_for_relative_proportional_spread_tests()

        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
