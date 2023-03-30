import configparser
import unittest
from pathlib import Path

from mdxpy import CalculatedMember, MdxBuilder, MdxHierarchySet, Member

from TM1py import Sandbox
from TM1py.Exceptions.Exceptions import TM1pyException, TM1pyVersionException, TM1pyWritePartialFailureException, \
    TM1pyWriteFailureException
from TM1py.Objects import (AnonymousSubset, Cube, Dimension, Element,
                           ElementAttribute, Hierarchy, MDXView, NativeView)
from TM1py.Services import TM1Service
from TM1py.Utils import Utils, element_names_from_element_unique_names, CaseAndSpaceInsensitiveDict, \
    CaseAndSpaceInsensitiveTuplesDict
from .Utils import skip_if_insufficient_version, skip_if_no_pandas

try:
    import pandas as pd
except ImportError:
    pass


class TestCellService(unittest.TestCase):
    tm1: TM1Service
    prefix = 'TM1py_Tests_Cell_'
    cube_name = prefix + "Cube"
    view_name = prefix + "View"
    dimension_names = [
        prefix + 'Dimension1',
        prefix + 'Dimension2',
        prefix + 'Dimension3']
    string_cube_name = prefix + "StringCube"
    string_dimension_names = [
        prefix + 'StringDimension1',
        prefix + 'StringDimension2',
        prefix + 'StringDimension3']
    cells_in_string_cube = {
        ('d1e1', 'd2e1', 'd3e1'): 'String1',
        ('d1e2', 'd2e2', 'd3e2'): 'String2',
        ('d1e3', 'd2e3', 'd3e3'): 'String3'}

    latin_1_encoded_text = "Èd5áÂè"

    cube_rps1_name = prefix + "Cube" + "_RPS1"
    cube_rps2_name = prefix + "Cube" + "_RPS2"

    cube_with_consolidations_name = cube_name + "_With_Consolidations"
    dimensions_with_consolidations_names = [
        dimension_name + "_With_Consolidations"
        for dimension_name in
        dimension_names]
    cube_with_rules_name = cube_name + "_With_Rules"

    dimension_rps1_name = prefix + "Dimension" + "_RPS1"
    dimension_rps2_name = prefix + "Dimension" + "_RPS2"

    sandbox_name = prefix + "sandbox"

    target_coordinates = list(zip(('Element ' + str(e) for e in range(1, 101)),
                                  ('Element ' + str(e) for e in range(1, 101)),
                                  ('Element ' + str(e) for e in range(1, 101))))

    dimension_with_hierarchies_name = prefix + "Dimension_With_Hierarchies"

    cube_with_five_dimensions = prefix + "Cube_with_five_dimensions"

    five_dimensions = [
        cube_with_five_dimensions + "_" + str(1),
        cube_with_five_dimensions + "_" + str(2),
        cube_with_five_dimensions + "_" + str(3),
        cube_with_five_dimensions + "_" + str(4),
        cube_with_five_dimensions + "_" + str(5)
    ]

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        # Build Dimensions
        for dimension_name in cls.dimension_names:
            elements = [Element('Element {}'.format(str(j)), 'Numeric')
                        for j
                        in range(1, 1001)]

            element_attributes = [ElementAttribute("Attr1", "String"),
                                  ElementAttribute("Attr2", "Numeric"),
                                  ElementAttribute("Attr3", "Numeric"),
                                  ElementAttribute("NA", "Numeric")]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements,
                                  element_attributes=element_attributes)
            dimension = Dimension(dimension_name, [hierarchy])
            if cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.update(dimension)
            else:
                cls.tm1.dimensions.update_or_create(dimension)
            attribute_cube = "}ElementAttributes_" + dimension_name
            attribute_values = {}
            for element in elements:
                attribute_values[(element.name, "Attr1")] = "TM1py"
                attribute_values[(element.name, "Attr2")] = "2"
                attribute_values[(element.name, "Attr3")] = "3"
                attribute_values[(element.name, "NA")] = "4"

            cls.tm1.cubes.cells.write_values(attribute_cube, attribute_values)

        # Build Cube
        cube = Cube(cls.cube_name, cls.dimension_names)
        if not cls.tm1.cubes.exists(cls.cube_name):
            cls.tm1.cubes.update_or_create(cube)

        # Build cube view
        view = NativeView(
            cube_name=cls.cube_name,
            view_name=cls.view_name,
            suppress_empty_columns=True,
            suppress_empty_rows=True)
        view.add_row(
            dimension_name=cls.dimension_names[0],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[0],
                expression='{[' + cls.dimension_names[0] + '].Members}'))
        view.add_row(
            dimension_name=cls.dimension_names[1],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[1],
                expression='{[' + cls.dimension_names[1] + '].Members}'))
        view.add_column(
            dimension_name=cls.dimension_names[2],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[2],
                expression='{[' + cls.dimension_names[2] + '].Members}'))
        if not cls.tm1.cubes.views.exists(cls.cube_name, view.name, private=False):
            cls.tm1.cubes.views.update_or_create(
                view=view,
                private=False)

        cls.build_cube_with_rules()

        cls.build_cube_with_consolidations()

        # For tests on string related methods
        cls.build_string_cube()

        cls.build_assets_for_relative_proportional_spread()

        cls.create_or_update_dimension_with_hierarchies()

        cls.create_cube_with_five_dimensions()

    @classmethod
    def setUp(cls):
        """
        Reset data before each test run
        """
        # set correct version before test, as it is overwritten in a test case
        cls.tm1._tm1_rest.set_version()

        # populate data in cube

        # cellset of data that shall be written
        cls.cellset = Utils.CaseAndSpaceInsensitiveTuplesDict()
        value = 1
        for element1, element2, element3 in cls.target_coordinates:
            cls.cellset[(element1, element2, element3)] = value

        # Sum of all the values that we write in the cube. serves as a checksum.
        cls.total_value = sum(cls.cellset.values())

        # Fill cube with values
        cls.tm1.cubes.cells.write_values(cls.cube_name, cls.cellset)

        cls.tm1.cubes.cells.write_values(cls.string_cube_name, cls.cells_in_string_cube)

        if not cls.tm1.sandboxes.exists(cls.sandbox_name):
            cls.tm1.sandboxes.create(Sandbox(cls.sandbox_name, True))

    @classmethod
    def tearDown(cls):
        """
        Clear data from cubes after each test run
        """
        cls.tm1.processes.execute_ti_code("CubeClearData('" + cls.cube_name + "');")
        cls.tm1.processes.execute_ti_code("CubeClearData('" + cls.string_cube_name + "');")
        cls.tm1.processes.execute_ti_code("CubeClearData('" + cls.cube_rps1_name + "');")
        cls.tm1.processes.execute_ti_code("CubeClearData('" + cls.cube_rps2_name + "');")

    @classmethod
    def build_string_cube(cls):
        if cls.tm1.cubes.exists(cls.string_cube_name):
            cls.tm1.cubes.delete(cls.string_cube_name)

        for d, dimension_name in enumerate(cls.string_dimension_names, start=1):
            dimension = Dimension(dimension_name)
            hierarchy = Hierarchy(dimension_name, dimension_name)
            for i in range(1, 5, 1):
                element_name = "d" + str(d) + "e" + str(i)
                hierarchy.add_element(element_name=element_name, element_type="String")
            dimension.add_hierarchy(hierarchy)
            cls.tm1.dimensions.update_or_create(dimension)

        cube = Cube(name=cls.string_cube_name, dimensions=cls.string_dimension_names)
        cls.tm1.elements.add_elements(
            dimension_name=cube.dimensions[-1],
            hierarchy_name=cube.dimensions[-1],
            elements=[Element("n1", "Numeric")])

        cls.tm1.cubes.update_or_create(cube)

    @classmethod
    def remove_string_cube(cls):
        if cls.tm1.cubes.exists(cube_name=cls.string_cube_name):
            cls.tm1.cubes.delete(cube_name=cls.string_cube_name)
        for dimension_name in cls.string_dimension_names:
            if cls.tm1.dimensions.exists(dimension_name=dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def build_cube_with_rules(cls):
        cube = Cube(name=cls.cube_with_rules_name, dimensions=cls.dimension_names)

        cube.rules = f"""
        ['{cls.dimension_names[0]}':'Element1'] = N: 1;\r\n
        ['{cls.dimension_names[0]}':'Element2'] = N: ['{cls.dimension_names[0]}':'Element1'] ;\r\n
        ['{cls.dimension_names[0]}':'Element3'] = N: ['{cls.dimension_names[0]}':'Element2'] ;\r\n
        """
        cls.tm1.cubes.update_or_create(cube)

    @classmethod
    def remove_cube_with_rules(cls):
        cls.tm1.cubes.delete(cls.cube_with_rules_name)

    @classmethod
    def build_cube_with_consolidations(cls):
        for dimension_name_source, dimension_name_target in zip(cls.dimension_names,
                                                                cls.dimensions_with_consolidations_names):
            dimension = cls.tm1.dimensions.get(dimension_name=dimension_name_source)
            dimension.name = dimension_name_target
            hierarchy = dimension.get_hierarchy(dimension_name_target)
            for element in hierarchy:
                hierarchy.add_edge(parent="TOTAL_" + dimension_name_target, component=element.name, weight=1)
            hierarchy.add_element("TOTAL_" + dimension_name_target, "Consolidated")
            cls.tm1.dimensions.update_or_create(dimension)

        cube = Cube(name=cls.cube_with_consolidations_name, dimensions=cls.dimensions_with_consolidations_names)
        cls.tm1.cubes.update_or_create(cube)

    @classmethod
    def remove_cube_with_consolidations(cls):
        if cls.tm1.cubes.exists(cube_name=cls.cube_with_consolidations_name):
            cls.tm1.cubes.delete(cube_name=cls.cube_with_consolidations_name)
        for dimension_name in cls.dimensions_with_consolidations_names:
            if cls.tm1.dimensions.exists(dimension_name=dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def create_cube_with_five_dimensions(cls):
        for dimension_name in cls.five_dimensions:
            hierarchy = Hierarchy(
                dimension_name=dimension_name,
                name=dimension_name,
                elements=[Element("e1", "Numeric"), Element("e2", "Numeric"), Element("e3", "Numeric")])
            dimension = Dimension(name=dimension_name, hierarchies=[hierarchy])
            cls.tm1.dimensions.update_or_create(dimension)
        cube = Cube(cls.cube_with_five_dimensions, dimensions=cls.five_dimensions)
        cls.tm1.cubes.update_or_create(cube)

        cells = {
            ("e1", "e1", "e1", "e1", "e1"): 1,
            ("e2", "e2", "e2", "e2", "e2"): 2,
            ("e3", "e3", "e3", "e3", "e3"): 3
        }
        cls.tm1.cells.write(cls.cube_with_five_dimensions, cells)

    @classmethod
    def remove_cube_with_five_dimensions(cls):
        if cls.tm1.cubes.exists(cube_name=cls.cube_with_five_dimensions):
            cls.tm1.cubes.delete(cube_name=cls.cube_with_five_dimensions)
        for dimension_name in cls.five_dimensions:
            if cls.tm1.dimensions.exists(dimension_name=dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def build_assets_for_relative_proportional_spread(cls):
        for dimension_name in (cls.dimension_rps1_name, cls.dimension_rps2_name):
            dimension = Dimension(dimension_name)
            hierarchy = Hierarchy(dimension_name, dimension_name)
            hierarchy.add_element(element_name="c1", element_type="Consolidated")
            for i in range(1, 5, 1):
                element_name = "e" + str(i)
                hierarchy.add_element(element_name=element_name, element_type="Numeric")
                hierarchy.add_edge(parent="c1", component=element_name, weight=1)
            dimension.add_hierarchy(hierarchy)
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.update_or_create(dimension)

        for cube_name in (cls.cube_rps1_name, cls.cube_rps2_name):
            cube = Cube(name=cube_name, dimensions=(cls.dimension_rps1_name, cls.dimension_rps2_name))
            if not cls.tm1.cubes.exists(cube.name):
                cls.tm1.cubes.update_or_create(cube)
            # zero out cube
            cls.tm1.processes.execute_ti_code("CubeClearData('" + cube_name + "');")

    @classmethod
    def remove_assets_for_relative_proportional_spread(cls):
        for cube_name in (cls.cube_rps1_name, cls.cube_rps2_name):
            if cls.tm1.cubes.exists(cube_name):
                cls.tm1.cubes.delete(cube_name=cube_name)
        for dimension_name in (cls.dimension_rps1_name, cls.dimension_rps2_name):
            if cls.tm1.dimensions.exists(dimension_name):
                cls.tm1.dimensions.delete(dimension_name=dimension_name)

    @classmethod
    def create_or_update_dimension_with_hierarchies(cls):
        dimension = Dimension(cls.dimension_with_hierarchies_name)
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy1",
                dimension_name=dimension.name,
                elements=[Element("Elem1", "Numeric"), Element("Elem2", "Numeric"), Element("Elem3", "Numeric")],
                element_attributes=[ElementAttribute("ea1", "String"), ElementAttribute("ea2", "String")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy2",
                dimension_name=dimension.name,
                elements=[Element("Elem4", "Numeric"), Element("Elem6", "Numeric"), Element("Cons1", "Consolidated")]))
        dimension.add_hierarchy(
            Hierarchy(
                name="Hierarchy3",
                dimension_name=dimension.name,
                elements=[Element("Elem5", "Numeric"), Element("Cons2", "Consolidated"),
                          Element("Cons3", "Consolidated")]))
        cls.tm1.dimensions.update_or_create(dimension)

        cells = {
            ("Hierarchy1:Elem1", "ea1"): "123",
            ("Hierarchy2:Cons1", "ea2"): "ABC",
            ("Hierarchy3:Cons2", "ea2"): "DEF"}
        cls.tm1.cells.write("}ElementAttributes_" + cls.dimension_with_hierarchies_name, cells, use_ti=True)

    def test_write_and_get_value(self):
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        response = self.tm1.cubes.cells.write_value(1, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, 1)
        response = self.tm1.cubes.cells.write_value(2, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, 2)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_get_value_iterator(self):
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1, Element2, Element3')
        response = self.tm1.cubes.cells.write_value(3, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name, (
            (self.dimension_names[0], 'Element1'),
            (self.dimension_names[1], 'EleMent2'),
            (self.dimension_names[2], 'ELEMENT  3')
        ))
        self.assertEqual(value, 3)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_write_and_get_value_hierarchy(self):
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        response = self.tm1.cubes.cells.write_value(4, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name,
                                               f'{self.dimension_names[0]}::Element1,EleMent2,{self.dimension_names[2]}::ELEMENT  3')
        self.assertEqual(value, 4)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_get_value_iterator_hierarchy(self):
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1, Element2, Element3')
        response = self.tm1.cubes.cells.write_value(5, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name, [
            (self.dimension_names[0], self.dimension_names[0], 'Element1'),
            (self.dimension_names[1], 'EleMent2'),
            Member.of(self.dimension_names[2], self.dimension_names[2], 'ELEMENT  3')
        ])
        self.assertEqual(value, 5)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_write_and_get_value_changed_separator(self):
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        response = self.tm1.cubes.cells.write_value(6, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(
            self.cube_name,
            f'{self.dimension_names[0]}$$Element1;EleMent2;{self.dimension_names[2]}  $$ ELEMENT  3',
            element_separator=";",
            hierarchy_element_separator="$$"
        )
        self.assertEqual(value, 6)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_get_value_old_interface(self):
        """ Tests if the old function interface with parameter element_string is still usable -> for backwards compatibility """
        original_value = self.tm1.cubes.cells.get_value(self.cube_name, 'Element1,EleMent2,ELEMENT  3')
        response = self.tm1.cubes.cells.write_value(7, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))
        self.assertTrue(response.ok)
        value = self.tm1.cubes.cells.get_value(self.cube_name, element_string='Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, 7)
        self.tm1.cubes.cells.write_value(original_value, self.cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test_write_values(self):
        cells = {("Element 2", "Element4", "Element7"): 716}

        self.tm1.cubes.cells.write_values(self.cube_name, cells)
        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 2]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 7]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [716])

    def test_write(self):
        cells = {("Element 1", "Element4", "Element9"): 717}
        self.tm1.cubes.cells.write(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [717])

    def test_write_use_ti(self):
        cells = {("Element 1", "Element4", "Element9"): 1234}
        self.tm1.cubes.cells.write(self.cube_name, cells, use_ti=True, use_changeset=False)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [1234])

    def test_write_use_blob(self):
        cells = {("Element 1", "Element4", "Element9"): 1234}
        self.tm1.cubes.cells.write(self.cube_name, cells, use_blob=True, use_changeset=False)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [1234])

    def test_write_use_ti_skip_non_updateable(self):
        cells = CaseAndSpaceInsensitiveTuplesDict()
        cells["Element 1", "Element4", "TOTAL_" + self.dimensions_with_consolidations_names[2]] = 5
        cells["Element 1", "Element22", "Element9"] = 8

        self.tm1.cells.write(self.cube_with_consolidations_name, cells, use_ti=True, skip_non_updateable=True)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 1]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 22]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_skip_non_updateable(self):
        cells = CaseAndSpaceInsensitiveTuplesDict()
        cells["Element 1", "Element4", "TOTAL_" + self.dimensions_with_consolidations_names[2]] = 5
        cells["Element 4", "Element7", "Element9"] = 8

        self.tm1.cells.write(self.cube_with_consolidations_name, cells, skip_non_updateable=True)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 4]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 7]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_increment_true(self):
        cells = {("Element 1", "Element5", "Element8"): 211}

        self.tm1.cubes.cells.write(self.cube_name, cells)
        self.tm1.cubes.cells.write(self.cube_name, cells, increment=True)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 5]",
            f"[{self.dimension_names[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [422])

    def test_write_increment_false(self):
        cells = {("Element 1", "Element5", "Element8"): 211}

        self.tm1.cubes.cells.write(self.cube_name, cells)
        self.tm1.cubes.cells.write(self.cube_name, cells, increment=False)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 5]",
            f"[{self.dimension_names[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [211])

    def test_write_through_unbound_process_happy_case(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 719
        self.tm1.cubes.cells.write_through_unbound_process(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [719])

    def test_write_through_unbound_process_sandbox(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 7192
        self.tm1.cubes.cells.write_through_unbound_process(self.cube_name, cells, sandbox_name=self.sandbox_name)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx(), sandbox_name=self.sandbox_name), [7192])

    def test_write_through_unbound_process_long_digit_as_str(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = '10000.123456789123456789123456789'
        self.tm1.cubes.cells.write_through_unbound_process(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [10000.1234567891])

    def test_write_through_unbound_process_str(self):
        cells = dict()
        cells["d1e1", "d2e4", "d3e3"] = 'TM1py Test'
        self.tm1.cubes.cells.write_through_unbound_process(self.string_cube_name, cells)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e4]",
            f"[{self.string_dimension_names[2]}].[d3e3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['TM1py Test'])

    def test_write_through_unbound_process_attributes(self):
        cells = dict()
        cells["element1", "Attr1"] = 'Text 1'
        cells["element1", "Attr2"] = 1
        cells["element1", "Attr3"] = 2
        cells["element2", "Attr1"] = ""
        cells["element2", "Attr2"] = 0
        cells["element2", "Attr3"] = None
        self.tm1.cubes.cells.write_through_unbound_process("}ElementAttributes_" + self.dimension_names[0], cells)

        query = MdxBuilder.from_cube("}ElementAttributes_" + self.dimension_names[0])
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr1]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr2]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr3]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr1]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr2]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr3]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['Text 1', 1, 2, "", None, None])

    def test_write_through_unbound_process_to_consolidation(self):
        cells = dict()
        cells["Element 1", "Element4", "TOTAL_" + self.dimensions_with_consolidations_names[2]] = 5
        cells["Element 1", "Element4", "Element3"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.cubes.cells.write_through_unbound_process(self.cube_with_consolidations_name, cells)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 1]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 4]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_through_unbound_process_to_not_existing_element(self):
        cells = dict()
        cells["Element 1", "Element4", "element6"] = 5
        cells["Element 1", "Element4", "Not Existing Element"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.cubes.cells.write_through_unbound_process(self.cube_with_consolidations_name, cells)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 1]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 4]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 6]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [5])

    def test_write_through_unbound_process_write_failure_exception(self):
        cells = dict()
        cells["Element 1", "Element4", "Not Existing Element 1"] = "Text 1"
        cells["Element 2", "Element8", "Element 9"] = 8

        with self.assertRaises(TM1pyWriteFailureException) as ex:
            self.tm1.cubes.cells.write_through_unbound_process(self.cube_with_consolidations_name, cells)
        self.assertEqual(ex.exception.statuses, ['Aborted'])
        self.assertIn(".log", ex.exception.error_log_files[0])

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 2]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 8]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 9]")

        self.assertEqual([8], self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()))

    def test_write_through_unbound_process_write_partial_failure_exception(self):
        cells = dict()
        cells["Element 2", "Element8", "Not Existing Element"] = 2
        cells["Element 2", "Element8", "Element 5"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException) as ex:
            self.tm1.cubes.cells.write_through_unbound_process(self.cube_with_consolidations_name, cells)
        self.assertEqual(ex.exception.statuses, ['HasMinorErrors'])
        self.assertEqual(ex.exception.attempts, 1)
        self.assertIn(".log", ex.exception.error_log_files[0])

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 2]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 8]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 5]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_through_unbound_process_line_break_hashmark_combo(self):
        cells = dict()
        cells["d1e1", "d2e4", "d3e3"] = 'TM1py \r\n#Test'

        self.tm1.cubes.cells.write_through_unbound_process(self.string_cube_name, cells)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e4]",
            f"[{self.string_dimension_names[2]}].[d3e3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['TM1py #Test'])

    def test_write_through_blob_happy_case(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 719
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [719])

    def test_write_through_blob_sandbox(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 7192
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells, sandbox_name=self.sandbox_name)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx(), sandbox_name=self.sandbox_name), [7192])

    def test_write_through_blob_long_digit_as_str(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = '10000.123456789123456789123456789'
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertAlmostEqual(
            self.tm1.cells.execute_mdx_values(mdx=query.to_mdx())[0],
            10000.1234567891,
            8)

    def test_write_through_blob_str(self):
        cells = dict()
        cells["d1e1", "d2e4", "d3e3"] = 'TM1py Test'
        self.tm1.cubes.cells.write_through_blob(self.string_cube_name, cells)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e4]",
            f"[{self.string_dimension_names[2]}].[d3e3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['TM1py Test'])

    def test_write_through_blob_attributes(self):
        cells = dict()
        cells["element1", "Attr1"] = 'Text 1'
        cells["element1", "Attr2"] = 1
        cells["element1", "Attr3"] = 2
        cells["element2", "Attr1"] = ""
        cells["element2", "Attr2"] = 0
        cells["element2", "Attr3"] = None
        self.tm1.cubes.cells.write_through_blob("}ElementAttributes_" + self.dimension_names[0], cells)

        query = MdxBuilder.from_cube("}ElementAttributes_" + self.dimension_names[0])
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr1]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr2]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element1]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr3]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr1]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr2]")
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[element2]",
            f"[}}ElementAttributes_{self.dimension_names[0]}].[Attr3]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['Text 1', 1, 2, "", None, None])

    def test_write_through_blob_to_consolidation(self):
        cells = dict()
        cells["Element 1", "Element4", "TOTAL_" + self.dimensions_with_consolidations_names[2]] = 5
        cells["Element 1", "Element4", "Element3"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.cubes.cells.write_through_blob(self.cube_with_consolidations_name, cells)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 1]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 4]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_through_blob_to_not_existing_element(self):
        cells = dict()
        cells["Element 1", "Element4", "element6"] = 5
        cells["Element 1", "Element4", "Not Existing Element"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException):
            self.tm1.cubes.cells.write_through_blob(self.cube_with_consolidations_name, cells)

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 1]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 4]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 6]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [5])

    def test_write_through_blob_write_failure_exception(self):
        cells = dict()
        cells["Element 1", "Element4", "Not Existing Element 1"] = "Text 1"
        cells["Element 2", "Element8", "Element 9"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException) as ex:
            self.tm1.cubes.cells.write_through_blob(self.cube_with_consolidations_name, cells)
        self.assertEqual(ex.exception.statuses, ['HasMinorErrors'])
        self.assertIn(".log", ex.exception.error_log_files[0])

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 2]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 8]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 9]")

        self.assertEqual([8], self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()))

    def test_write_through_blob_write_partial_failure_exception(self):
        cells = dict()
        cells["Element 2", "Element8", "Not Existing Element"] = 2
        cells["Element 2", "Element8", "Element 5"] = 8

        with self.assertRaises(TM1pyWritePartialFailureException) as ex:
            self.tm1.cubes.cells.write_through_blob(self.cube_with_consolidations_name, cells)
        self.assertEqual(ex.exception.statuses, ['HasMinorErrors'])
        self.assertEqual(ex.exception.attempts, 1)
        self.assertIn(".log", ex.exception.error_log_files[0])

        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimensions_with_consolidations_names[0]}].[Element 2]",
            f"[{self.dimensions_with_consolidations_names[1]}].[Element 8]",
            f"[{self.dimensions_with_consolidations_names[2]}].[Element 5]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [8])

    def test_write_through_blob_line_break_hashmark_combo(self):
        cells = dict()
        cells["d1e1", "d2e4", "d3e3"] = 'TM1py \r\n#Test'

        self.tm1.cubes.cells.write_through_blob(self.string_cube_name, cells)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e4]",
            f"[{self.string_dimension_names[2]}].[d3e3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['TM1py #Test'])

    def test_undo_cellset_write(self):
        cells = dict()
        cells["Element 12", "Element 13", "Element 15"] = 3.3

        changeset = self.tm1.cells.write(self.cube_name, cells, use_changeset=True)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 12]",
            f"[{self.dimension_names[1]}].[Element 13]",
            f"[{self.dimension_names[2]}].[Element 15]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [3.3])

        self.tm1.cells.undo_changeset(changeset=changeset)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 12]",
            f"[{self.dimension_names[1]}].[Element 13]",
            f"[{self.dimension_names[2]}].[Element 15]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [None])

    def test_undo_cellset_write_values(self):
        cells = dict()
        cells["Element 16", "Element 13", "Element 15"] = 3.6

        changeset = self.tm1.cells.write_values(self.cube_name, cells, use_changeset=True)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 16]",
            f"[{self.dimension_names[1]}].[Element 13]",
            f"[{self.dimension_names[2]}].[Element 15]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [3.6])

        self.tm1.cells.undo_changeset(changeset=changeset)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 16]",
            f"[{self.dimension_names[1]}].[Element 13]",
            f"[{self.dimension_names[2]}].[Element 15]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [None])

    def test_write_through_blob_multi_str(self):
        cells = dict()
        cells["d1e1", "d2e4", "d3e3"] = 'TM1py Test1'
        cells["d1e1", "d2e2", "d3e3"] = 'TM1py Test2'
        self.tm1.cubes.cells.write_through_blob(self.string_cube_name, cells)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e4]",
            f"[{self.string_dimension_names[2]}].[d3e3]")
        query.add_member_tuple_to_columns(
            f"[{self.string_dimension_names[0]}].[d1e1]",
            f"[{self.string_dimension_names[1]}].[d2e2]",
            f"[{self.string_dimension_names[2]}].[d3e3]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), ['TM1py Test1', 'TM1py Test2'])

    def test_write_through_blob_scientific_notation_small(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = "{:e}".format(0.00000001)
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [0.00000001])

    def test_write_through_blob_scientific_notation_large(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = "{:e}".format(12_300_000_000)
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [12_300_000_000])

    def test_write_through_blob_multi_cells(self):
        cells = dict()
        cells["Element 1", "Element4", "Element9"] = 702
        cells["Element 2", "Element4", "Element7"] = 701
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 9]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [702])

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 2]",
            f"[{self.dimension_names[1]}].[Element 4]",
            f"[{self.dimension_names[2]}].[Element 7]")
        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [701])

    def test_write_through_blob_increment_true(self):
        cells = {("Element 1", "Element5", "Element8"): 111}

        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells, increment=True)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 5]",
            f"[{self.dimension_names[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [222])

    def test_write_through_blob_increment_false(self):
        cells = {("Element 1", "Element5", "Element8"): 109}

        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells)
        self.tm1.cubes.cells.write_through_blob(self.cube_name, cells, increment=False)

        query = MdxBuilder.from_cube(self.cube_name)
        query.add_member_tuple_to_columns(
            f"[{self.dimension_names[0]}].[Element 1]",
            f"[{self.dimension_names[1]}].[Element 5]",
            f"[{self.dimension_names[2]}].[Element 8]")

        self.assertEqual(self.tm1.cells.execute_mdx_values(mdx=query.to_mdx()), [109])

    @skip_if_no_pandas
    def test_write_dataframe(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 1", "element 1"],
            self.dimension_names[1]: ["element 1", "element 2", "element 3"],
            self.dimension_names[2]: ["element 5", "element 5", "element 5"],
            "Value": [1.0, 2.0, 3.0]})
        self.tm1.cubes.cells.write_dataframe(self.cube_name, df)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "element 1"),
            Member.of(self.dimension_names[1], "element 2"),
            Member.of(self.dimension_names[1], "element 3")]))

        query = query.add_member_to_where(Member.of(self.dimension_names[2], "element 5"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(list(df["Value"]), values)

    @skip_if_no_pandas
    def test_write_dataframe_duplicate_numeric_entries(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 1", "element 1"],
            self.dimension_names[1]: ["element 1", "element 1", "element 1"],
            self.dimension_names[2]: ["element 1", "element 1", "element 1"],
            "Value": [1.0, 2.0, 3.0]})
        self.tm1.cubes.cells.write_dataframe(self.cube_name, df)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "element 1")]))

        query = query.add_member_to_where(Member.of(self.dimension_names[2], "element 1"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual([6], values)

    @skip_if_no_pandas
    def test_write_dataframe_duplicate_numeric_and_string_entries(self):
        df = pd.DataFrame({
            self.string_dimension_names[0]: ["d1e1", "d1e1", "d1e1", "d1e1", "d1e1"],
            self.string_dimension_names[1]: ["d2e1", "d2e1", "d2e1", "d2e1", "d2e1"],
            self.string_dimension_names[2]: ["d3e1", "d3e2", "d3e2", "n1", "n1"],
            "Value": ["text1", "text2", "text3", 3.0, 4.0]})
        self.tm1.cubes.cells.write_dataframe(self.string_cube_name, df)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[0], "d1e1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.string_dimension_names[1], "d2e1")]))
        query = query.add_member_to_where(Member.of(self.string_dimension_names[2], "n1"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual([7], values)

        query = MdxBuilder.from_cube(self.string_cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.members([
                Member.of(self.string_dimension_names[2], "d3e1"),
                Member.of(self.string_dimension_names[2], "d3e2")]))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.string_dimension_names[1], "d2e1")]))
        query = query.add_member_to_where(Member.of(self.string_dimension_names[0], "d1e1"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual(["text1", "text3"], values)

    @skip_if_no_pandas
    def test_write_dataframe_error(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 3", "element 5"],
            self.dimension_names[1]: ["element 1", "element 2", "element 4"],
            self.dimension_names[2]: ["element 1", "element 3", "element 5"],
            "Extra Column": ["element 1", "element2", "element3"],
            "Value": [1, 2, 3]})
        with self.assertRaises(ValueError) as _:
            self.tm1.cubes.cells.write_dataframe(self.cube_name, df)

    @skip_if_no_pandas
    def test_write_dataframe_async(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 1", "element 1"],
            self.dimension_names[1]: ["element 1", "element 2", "element 3"],
            self.dimension_names[2]: ["element 5", "element 5", "element 5"],
            "Value": [1, 2, 3]})
        self.tm1.cubes.cells.write_dataframe_async(self.cube_name, df, 1, 3)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "element 1"),
            Member.of(self.dimension_names[1], "element 2"),
            Member.of(self.dimension_names[1], "element 3")]))
        query = query.add_member_to_where(Member.of(self.dimension_names[2], "element 5"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(list(df["Value"]), values)

    @skip_if_no_pandas
    def test_write_dataframe_async_value_error(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 3", "element 5"],
            self.dimension_names[1]: ["element 1", "element 2", "element 4"],
            self.dimension_names[2]: ["element 1", "element 3", "element 5"],
            "Extra Column": ["element 1", "element2", "element3"],
            "Value": [1, 2, 3]})
        with self.assertRaises(ValueError) as _:
            self.tm1.cubes.cells.write_dataframe_async(self.cube_name, df, 1, 3)

    @skip_if_no_pandas
    def test_write_dataframe_async_minor_error(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 1", "element 1", "element 1", "element 1"],
            self.dimension_names[1]: ["element 2", "element 2", "element 2", "element 2", "element 2"],
            self.dimension_names[2]: ["Not Existing", "element 2", "element 3", "element 4", "Not Existing"],
            "Value": [1, 2, 3, 4, 5]})

        with self.assertRaises(TM1pyWritePartialFailureException) as ex:
            self.tm1.cubes.cells.write_dataframe_async(self.cube_name, df, 1, 5)
        self.assertEqual(2, ex.exception.attempts)
        self.assertEqual(['HasMinorErrors', 'HasMinorErrors'], ex.exception.statuses)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[2], "element 2"),
            Member.of(self.dimension_names[2], "element 3"),
            Member.of(self.dimension_names[2], "element 4")]))
        query = query.add_member_to_where(Member.of(self.dimension_names[1], "element 2"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(list(df["Value"])[1:-1], values)

    @skip_if_no_pandas
    def test_write_dataframe_error(self):
        df = pd.DataFrame({
            self.dimension_names[0]: ["element 1", "element 3", "element 5"],
            self.dimension_names[1]: ["element 1", "element 2", "element 4"],
            self.dimension_names[2]: ["element 1", "element 3", "element 5"],
            "Extra Column": ["element 1", "element2", "element3"],
            "Value": [1, 2, 3]})
        with self.assertRaises(ValueError) as _:
            self.tm1.cubes.cells.write_dataframe(self.cube_name, df)

    def test_write_async(self):
        cells = {
            ("element 1", "element 1", "element 5"): 1.59,
            ("element 1", "element 2", "element 5"): 2.87,
            ("element 1", "element 3", "element 5"): 3.12}

        self.tm1.cubes.cells.write_async(self.cube_name, cells, 1, 3)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "element 1"),
            Member.of(self.dimension_names[1], "element 2"),
            Member.of(self.dimension_names[1], "element 3")]))
        query = query.add_member_to_where(Member.of(self.dimension_names[2], "element 5"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(list(cells.values()), values)

    @skip_if_no_pandas
    def test_write_async_minor_errors(self):
        cells = {
            ("element 1", "element 2", "Not Existing1"): 0.612,
            ("element 1", "element 2", "element 2"): -9.87,
            ("element 1", "element 2", "element 3"): 1000,
            ("element 1", "element 2", "element 4"): 12345,
            ("element 1", "element 2", "Not Existing2"): 12.345}

        with self.assertRaises(TM1pyWritePartialFailureException) as ex:
            self.tm1.cubes.cells.write_async(self.cube_name, cells, 1, 5)
        self.assertEqual(2, ex.exception.attempts)
        self.assertEqual(['HasMinorErrors', 'HasMinorErrors'], ex.exception.statuses)

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element 1")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[2], "element 2"),
            Member.of(self.dimension_names[2], "element 3"),
            Member.of(self.dimension_names[2], "element 4")]))
        query = query.add_member_to_where(Member.of(self.dimension_names[1], "element 2"))
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(list(cells.values())[1:-1], values)

    def test_relative_proportional_spread_happy_case(self):
        """
        Tests that relative proportional spread populates a cube with the expected values
        """

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(self.cube_rps1_name, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=self.cube_rps1_name,
            unique_element_names=("[" + self.dimension_rps1_name + "].[e2]", "[" + self.dimension_rps2_name + "].[c1]"),
            reference_cube=self.cube_rps1_name,
            reference_unique_element_names=(
                "[" + self.dimension_rps1_name + "].[c1]", "[" + self.dimension_rps2_name + "].[c1]"))

        query = MdxBuilder.from_cube(self.cube_rps1_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_rps1_name, "e2")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_rps2_name, "e1"),
            Member.of(self.dimension_rps2_name, "e2"),
            Member.of(self.dimension_rps2_name, "e3")]))

        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())

        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_with_explicit_hierarchies(self):

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(self.cube_rps1_name, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=self.cube_rps1_name,
            unique_element_names=("[" + self.dimension_rps1_name + "].[" + self.dimension_rps1_name + "].[e2]",
                                  "[" + self.dimension_rps2_name + "].[" + self.dimension_rps2_name + "].[c1]"),
            reference_cube=self.cube_rps1_name,
            reference_unique_element_names=(
                "[" + self.dimension_rps1_name + "].[" + self.dimension_rps1_name + "].[c1]",
                "[" + self.dimension_rps2_name + "].[" + self.dimension_rps2_name + "].[c1]"))

        query = MdxBuilder.from_cube(self.cube_rps1_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_rps1_name, "e2")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_rps2_name, "e1"),
            Member.of(self.dimension_rps2_name, "e2"),
            Member.of(self.dimension_rps2_name, "e3")]))

        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_spread_without_reference_cube(self):

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(self.cube_rps1_name, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=self.cube_rps1_name,
            unique_element_names=("[" + self.dimension_rps1_name + "].[e2]", "[" + self.dimension_rps2_name + "].[c1]"),
            reference_unique_element_names=(
                "[" + self.dimension_rps1_name + "].[c1]", "[" + self.dimension_rps2_name + "].[c1]"))

        query = MdxBuilder.from_cube(self.cube_rps1_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_rps1_name, "e2")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_rps2_name, "e1"),
            Member.of(self.dimension_rps2_name, "e2"),
            Member.of(self.dimension_rps2_name, "e3")]))

        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_relative_proportional_spread_with_different_reference_cube(self):

        cells = {
            ('e1', 'e1'): 1,
            ('e1', 'e2'): 2,
            ('e1', 'e3'): 3,
        }
        self.tm1.cubes.cells.write_values(self.cube_rps2_name, cells)

        self.tm1.cubes.cells.relative_proportional_spread(
            value=12,
            cube=self.cube_rps1_name,
            unique_element_names=("[" + self.dimension_rps1_name + "].[e2]", "[" + self.dimension_rps2_name + "].[c1]"),
            reference_cube=self.cube_rps2_name,
            reference_unique_element_names=(
                "[" + self.dimension_rps1_name + "].[c1]", "[" + self.dimension_rps2_name + "].[c1]"))

        query = MdxBuilder.from_cube(self.cube_rps1_name)
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_rps1_name, "e2")))
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_rps2_name, "e1"),
            Member.of(self.dimension_rps2_name, "e2"),
            Member.of(self.dimension_rps2_name, "e3")]))

        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual(values[0], 2)
        self.assertEqual(values[1], 4)
        self.assertEqual(values[2], 6)

    def test_execute_mdx(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(
            self.total_value, sum(v["Value"] for v in data.values() if v["Value"])
        )

    def test_execute_mdx_top(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        # MDX with top
        data = self.tm1.cubes.cells.execute_mdx(mdx, top=5)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(len(data), 5)

    def test_execute_mdx_calculated_member(self):
        # MDX Query with calculated MEMBER
        mdx = """
        WITH MEMBER[{}].[{}] AS 2 
        SELECT[{}].MEMBERS ON ROWS, 
        {{[{}].[{}]}} ON COLUMNS 
        FROM[{}] 
        WHERE([{}].DefaultMember)""".format(
            self.dimension_names[1], "Calculated Member", self.dimension_names[0],
            self.dimension_names[1], "Calculated Member", self.cube_name, self.dimension_names[2])

        data = self.tm1.cubes.cells.execute_mdx(mdx, cell_properties=["Value", "Ordinal"])
        self.assertEqual(1000, len(data))
        self.assertEqual(2000, sum(v["Value"] for v in data.values()))
        self.assertEqual(sum(range(1000)), sum(v["Ordinal"] for v in data.values()))

    def test_execute_mdx_compact_json(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, use_compact_json=True)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(self.total_value, sum(v["Value"] for v in data.values() if v["Value"]))

    def test_execute_mdx_without_rows(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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

    def test_execute_mdx_with_empty_rows(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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

    def test_execute_mdx_with_empty_columns(self):
        # write cube content
        self.tm1.cubes.cells.write_values(self.cube_name, self.cellset)

        # MDX Query that gets full cube content with zero suppression
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty().add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_contexts=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                self.dimension_names[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                self.dimension_names[1])

    def test_execute_mdx_skip_consolidated(self):
        query = MdxBuilder.from_cube(self.cube_with_consolidations_name)
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(
                self.dimensions_with_consolidations_names[0],
                "Total_" + self.dimensions_with_consolidations_names[0]),
            Member.of(
                self.dimensions_with_consolidations_names[0],
                "Element1")]))
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimensions_with_consolidations_names[1], "Element1")))
        query = query.add_member_to_where("[" + self.dimensions_with_consolidations_names[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx(query.to_mdx(), skip_contexts=True, skip_consolidated_cells=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                self.dimensions_with_consolidations_names[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                self.dimensions_with_consolidations_names[1])

    def test_execute_mdx_skip_rule_derived(self):
        query = MdxBuilder.from_cube(self.cube_with_rules_name)
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[0], "Element 1"),
            Member.of(self.dimension_names[0], "Element 4")]))
        query = query.add_hierarchy_set_to_column_axis(MdxHierarchySet.member(
            Member.of(self.dimension_names[1], "Element1")))
        query = query.add_member_to_where("[" + self.dimension_names[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx(query.to_mdx(), skip_contexts=True, skip_rule_derived_cells=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                self.dimension_names[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                self.dimension_names[1])

    def test_execute_mdx_skip_zeros(self):
        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[0], "Element 1"),
            Member.of(self.dimension_names[0], "Element 2")]))
        query.add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1")))
        query.add_member_to_where("[" + self.dimension_names[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx(query.to_mdx(), skip_contexts=False, skip_zeros=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 3)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                self.dimension_names[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                self.dimension_names[1])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[2]),
                self.dimension_names[2])

    def test_execute_mdx_unique_element_names_false(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([Member.of(self.dimension_names[0], "Element 1")])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element2"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element3]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, element_unique_names=False)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(coordinates, ("Element 1", "Element 2", "Element 3"))

    def test_execute_mdx_skip_cell_properties_true(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.members([Member.of(self.dimension_names[0], "Element 1")])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx(mdx, skip_cell_properties=True)

        self.assertEqual(len(data), 1)
        for coordinates, value in data.items():
            self.assertEqual(1, value)

    def test_execute_mdx_multi_axes(self):
        query = MdxBuilder.from_cube(self.cube_with_five_dimensions)
        for axis, dimension in enumerate(self.five_dimensions):
            query.non_empty(axis)
            query.add_hierarchy_set_to_axis(axis, MdxHierarchySet.all_leaves(dimension, dimension))

        cells = self.tm1.cells.execute_mdx(
            mdx=query.to_mdx(),
            element_unique_names=False,
            skip_cell_properties=True,
            skip_zeros=True)

        expected_cells = {
            ("e1", "e1", "e1", "e1", "e1"): 1,
            ("e2", "e2", "e2", "e2", "e2"): 2,
            ("e3", "e3", "e3", "e3", "e3"): 3
        }

        self.assertEqual(expected_cells, cells)

    def test_execute_mdx_multi_axes_with_where(self):
        query = MdxBuilder.from_cube(self.cube_with_five_dimensions)
        query.non_empty(0)
        query.add_hierarchy_set_to_axis(0, MdxHierarchySet.all_leaves(
            self.five_dimensions[0],
            self.five_dimensions[0]))

        query.non_empty(1)
        query.add_hierarchy_set_to_axis(1, MdxHierarchySet.all_leaves(
            self.five_dimensions[1],
            self.five_dimensions[1]))

        query.non_empty(2)
        query.add_hierarchy_set_to_axis(2, MdxHierarchySet.all_leaves(
            self.five_dimensions[2],
            self.five_dimensions[2]))

        query.non_empty(3)
        query.add_hierarchy_set_to_axis(3, MdxHierarchySet.all_leaves(
            self.five_dimensions[3],
            self.five_dimensions[3]))

        query.where(Member(self.five_dimensions[4], self.five_dimensions[4], "e2"))

        cells = self.tm1.cells.execute_mdx(
            mdx=query.to_mdx(),
            element_unique_names=False,
            skip_cell_properties=True,
            skip_zeros=True)

        expected_cells = {
            ("e2", "e2", "e2", "e2", "e2"): 2
        }

        self.assertEqual(expected_cells, cells)

    def test_execute_mdx_raw_skip_contexts(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        raw_response = self.tm1.cubes.cells.execute_mdx_raw(
            mdx,
            skip_contexts=True,
            member_properties=["UniqueName"])

        self.assertEqual(len(raw_response["Axes"]), 2)
        for axis in raw_response["Axes"]:
            dimension_on_axis = Utils.dimension_name_from_element_unique_name(
                axis["Tuples"][0]["Members"][0]["UniqueName"])
            self.assertNotEqual(dimension_on_axis, self.dimension_names[2])

    def test_execute_mdx_raw_include_hierarchies(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        raw_response = self.tm1.cubes.cells.execute_mdx_raw(mdx, include_hierarchies=True)

        for axis_counter, axis in enumerate(raw_response['Axes']):
            hierarchies = axis['Hierarchies']

            self.assertEqual(self.dimension_names[axis_counter], hierarchies[0]['Name'])
            self.assertEqual(self.dimension_names[axis_counter], hierarchies[0]['Dimension']['Name'])

    def test_execute_mdx_rows_and_values_one_cell(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_axis(1, MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_axis(0, MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, self.dimension_names[0])
            self.assertEqual(len(cells), 1)

    def test_execute_mdx_rows_and_values_empty_cellset(self):
        # make sure it's empty
        self.tm1.cubes.cells.write_values(self.cube_name, {("Element10", "Element11", "Element13"): 0})

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element10"))) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element11"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element13]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=True)
        self.assertEqual(len(data), 0)

    def test_execute_mdx_rows_and_values_member_names(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element1"))) \
            .add_member_to_where("[" + self.dimension_names[2] + "].[Element1]").to_mdx()

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(mdx, element_unique_names=False)

        self.assertEqual(len(data), 1)
        for row, cells in data.items():
            member_name = row[0]
            self.assertEqual(member_name, "Element 1")

    def test_execute_mdx_rows_and_values_one_dimension_on_rows(self):
        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[0], "Element1"),
            Member.of(self.dimension_names[0], "Element2")]))
        query = query.add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "Element1"),
            Member.of(self.dimension_names[1], "Element2"),
            Member.of(self.dimension_names[1], "Element3")]))
        query = query.where("[" + self.dimension_names[2] + "].[Element1]")

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(query.to_mdx())

        self.assertEqual(len(data), 2)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, self.dimension_names[0])
            self.assertEqual(len(cells), 3)

    def test_execute_mdx_rows_and_values_two_dimensions_on_rows(self):

        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_axis(0, MdxHierarchySet.members([
            Member.of(self.dimension_names[2], "Element1"),
            Member.of(self.dimension_names[2], "Element2"),
            Member.of(self.dimension_names[2], "Element3")]))
        query = query.add_hierarchy_set_to_axis(1, MdxHierarchySet.members([
            Member.of(self.dimension_names[0], "Element1"),
            Member.of(self.dimension_names[0], "Element2")]))
        query = query.add_hierarchy_set_to_axis(1, MdxHierarchySet.members([
            Member.of(self.dimension_names[1], "Element1"),
            Member.of(self.dimension_names[1], "Element2")]))

        data = self.tm1.cubes.cells.execute_mdx_rows_and_values(query.to_mdx())

        self.assertEqual(len(data), 4)
        for row, cells in data.items():
            self.assertEqual(len(row), 2)
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, self.dimension_names[0])
            dimension = Utils.dimension_name_from_element_unique_name(row[1])
            self.assertEqual(dimension, self.dimension_names[1])
            self.assertEqual(len(cells), 3)

    def test_execute_mdx_raw_with_member_properties_with_elem_properties(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
        self.tm1.cells.write_values(self.cube_name, self.cellset)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
              "WHERE([{}].DefaultMember)".format(self.dimension_names[1], "Calculated Member", self.dimension_names[0],
                                                 self.dimension_names[1], "Calculated Member", self.cube_name,
                                                 self.dimension_names[2])

        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            1000,
            len(list(data)))
        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            2000,
            sum(data))

    def test_execute_mdx_values_compact_json(self):
        self.tm1.cells.write_values(self.cube_name, self.cellset)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        cell_values = self.tm1.cubes.cells.execute_mdx_values(mdx, use_compact_json=True)
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
              "WHERE([{}].DefaultMember)".format(self.dimension_names[1], "Calculated Member", self.dimension_names[0],
                                                 self.dimension_names[1], "Calculated Member", self.cube_name,
                                                 self.dimension_names[2])

        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            1000,
            len(list(data)))
        data = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(
            2000,
            sum(data))

    def test_execute_mdx_values_skip_zeros(self):
        cells = {
            ('Element 1', 'Element 3', 'Element 9'): 128
        }
        self.tm1.cells.write(self.cube_name, cells)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element1"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element 3"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.members(
            [Member.of(self.dimension_names[2], "Element 9"), Member.of(self.dimension_names[2], "Element 10")])) \
            .to_mdx()
        values = self.tm1.cells.execute_mdx_values(mdx, skip_zeros=True)

        self.assertEqual([128], values)

    def test_execute_mdx_csv(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(self.dimension_names + ["Value"]),
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

    def test_execute_mdx_csv_use_iterative_json(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, use_iterative_json=True)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(self.dimension_names + ["Value"]),
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

    def test_execute_mdx_csv_column_only(self):
        mdx = """SELECT
                    NON EMPTY {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].MEMBERS} * 
                    {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].MEMBERS} * 
                    {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].MEMBERS} ON 0
                    FROM [TM1PY_TESTS_CELL_CUBE]"""

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(self.dimension_names + ["Value"]),
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element9"))) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element 18"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[2], "Element 2"))) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        self.assertEqual("", csv)

    def test_execute_mdx_csv_skip_rule_derived(self):
        mdx = MdxBuilder.from_cube(self.cube_with_rules_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(100)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2]).head(100)) \
            .add_member_to_where(Member.of(self.dimension_names[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, skip_rule_derived_cells=True)

        self.assertEqual("", csv)

    def test_execute_mdx_csv_top(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2]).head(10)) \
            .add_member_to_where(Member.of(self.dimension_names[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, top=10, skip_zeros=False)

        records = csv.split("\r\n")
        self.assertEqual(11, len(records))

    def test_execute_mdx_csv_skip(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2]).head(10)) \
            .add_member_to_where(Member.of(self.dimension_names[0], "Element1")) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx, skip=10, skip_zeros=False)

        records = csv.split("\r\n")
        self.assertEqual(91, len(records))

    def test_execute_mdx_csv_with_calculated_member(self):
        # MDX Query with calculated MEMBER
        mdx = MdxBuilder.from_cube(self.cube_name).with_member(CalculatedMember.lookup_attribute(
            self.dimension_names[1],
            self.dimension_names[1],
            "Calculated Member",
            self.dimension_names[0],
            "Attr3")) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[1], "Calculated Member"))) \
            .to_mdx()

        csv = self.tm1.cubes.cells.execute_mdx_csv(mdx)

        # check header
        header = csv.split('\r\n')[0]
        self.assertEqual(
            ",".join(self.dimension_names[0:2] + ["Value"]),
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
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
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {
            tuple(row)
            for row
            in df[[*self.dimension_names]].values}
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
    def test_execute_mdx_dataframe_na_element_name(self):
        attribute_dimension = "}ElementAttributes_" + self.dimension_names[0]
        query = MdxBuilder.from_cube(attribute_dimension)
        query.add_hierarchy_set_to_column_axis(MdxHierarchySet.member(f"[{attribute_dimension}].[NA]"))
        query.add_hierarchy_set_to_column_axis(MdxHierarchySet.member(f"[{self.dimension_names[0]}].[Element 1]"))

        df = self.tm1.cubes.cells.execute_mdx_dataframe(query.to_mdx())
        self.assertEqual(
            [["NA", "Element 1", 4.0]],
            df.values.tolist())

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_use_iterative_json(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, use_iterative_json=True)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {
            tuple(row)
            for row
            in df[[*self.dimension_names]].values}
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
    def test_execute_mdx_dataframe_column_only(self):
        mdx = """SELECT
                    NON EMPTY {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].MEMBERS} * 
                    {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].MEMBERS} * 
                    {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].MEMBERS} ON 0
                    FROM [TM1PY_TESTS_CELL_CUBE]"""

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {
            tuple(row)
            for row
            in df[[*self.dimension_names]].values}
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
    def test_execute_mdx_dataframe_column_only_use_iterative_json(self):
        mdx = """SELECT
                        NON EMPTY {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].MEMBERS} * 
                        {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].MEMBERS} * 
                        {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].MEMBERS} ON 0
                        FROM [TM1PY_TESTS_CELL_CUBE]"""

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, use_iterative_json=True)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {
            tuple(row)
            for row
            in df[[*self.dimension_names]].values}
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
    def test_execute_mdx_dataframe_include_attributes(self):
        mdx = """SELECT
        NON EMPTY 
        {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].[Element1]} 
        PROPERTIES [TM1PY_TESTS_CELL_DIMENSION1].[ATTR1]  ON 0,
        NON EMPTY
        {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].[Element1]} * 
        {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].[Element1]} 
        PROPERTIES [TM1PY_TESTS_CELL_DIMENSION2].[ATTR2], [TM1PY_TESTS_CELL_DIMENSION3].[ATTR3] ON 1
        FROM [TM1PY_TESTS_CELL_CUBE]
        """

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, include_attributes=True)

        expected = {
            'TM1py_Tests_Cell_Dimension3': {0: 'Element 1'},
            'Attr3': {0: '3'},
            'TM1py_Tests_Cell_Dimension2': {0: 'Element 1'},
            'Attr2': {0: '2'},
            'TM1py_Tests_Cell_Dimension1': {0: 'Element 1'},
            'Attr1': {0: 'TM1py'},
            'Value': {0: 1.0}}
        self.assertEqual(expected, df.to_dict())

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_include_attributes_iter_json(self):
        mdx = """SELECT
        NON EMPTY 
        {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].[Element1]} 
        PROPERTIES [TM1PY_TESTS_CELL_DIMENSION1].[ATTR1]  ON 0,
        NON EMPTY
        {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].[Element1]} * 
        {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].[Element1]} 
        PROPERTIES [TM1PY_TESTS_CELL_DIMENSION2].[ATTR2], [TM1PY_TESTS_CELL_DIMENSION3].[ATTR3] ON 1
        FROM [TM1PY_TESTS_CELL_CUBE]
        """

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, include_attributes=True, use_iterative_json=True)

        expected = {
            'TM1py_Tests_Cell_Dimension3': {0: 'Element 1'},
            'Attr3': {0: '3'},
            'TM1py_Tests_Cell_Dimension2': {0: 'Element 1'},
            'Attr2': {0: '2'},
            'TM1py_Tests_Cell_Dimension1': {0: 'Element 1'},
            'Attr1': {0: 'TM1py'},
            'Value': {0: 1.0}}
        self.assertEqual(expected, df.to_dict())

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_include_attributes_iter_json_all_columns(self):
        mdx = """SELECT
        NON EMPTY 
        {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].[Element1]} *
        {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].[Element1]} *
        {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].[Element1]}
        PROPERTIES [TM1PY_TESTS_CELL_DIMENSION1].[ATTR1], [TM1PY_TESTS_CELL_DIMENSION2].[ATTR2],
        [TM1PY_TESTS_CELL_DIMENSION3].[ATTR3]  ON 0
        FROM [TM1PY_TESTS_CELL_CUBE]
        """

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, include_attributes=True, use_iterative_json=True)

        expected = {
            'TM1py_Tests_Cell_Dimension1': {0: 'Element 1'},
            'Attr1': {0: 'TM1py'},
            'TM1py_Tests_Cell_Dimension2': {0: 'Element 1'},
            'Attr2': {0: '2'},
            'TM1py_Tests_Cell_Dimension3': {0: 'Element 1'},
            'Attr3': {0: '3'},
            'Value': {0: 1.0}}
        self.assertEqual(expected, df.to_dict())

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_include_attributes_iter_json_no_attributes(self):
        mdx = """SELECT
        {[TM1PY_TESTS_CELL_DIMENSION1].[TM1PY_TESTS_CELL_DIMENSION1].[Element2]} *
        {[TM1PY_TESTS_CELL_DIMENSION2].[TM1PY_TESTS_CELL_DIMENSION2].[Element2]} *
        {[TM1PY_TESTS_CELL_DIMENSION3].[TM1PY_TESTS_CELL_DIMENSION3].[Element2]} 
         PROPERTIES MEMBER_NAME
        ON 0
        FROM [TM1PY_TESTS_CELL_CUBE]
        """

        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx, include_attributes=True, use_iterative_json=True)

        expected = {
            'TM1py_Tests_Cell_Dimension1': {0: 'Element 2'},
            'TM1py_Tests_Cell_Dimension2': {0: 'Element 2'},
            'TM1py_Tests_Cell_Dimension3': {0: 'Element 2'},
            'Value': {0: 1.0}}
        self.assertEqual(expected, df.to_dict())

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_pivot(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0]).head(7)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(8)) \
            .where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 8))

    @skip_if_no_pandas
    def test_execute_mdx_dataframe_pivot_no_titles(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0]).head(7)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(5)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2]).head(5)) \
            .to_mdx()

        pivot = self.tm1.cubes.cells.execute_mdx_dataframe_pivot(mdx=mdx)
        self.assertEqual(pivot.shape, (7, 5 * 5))

    def test_execute_mdx_cellcount(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        cell_count = self.tm1.cubes.cells.execute_mdx_cellcount(mdx)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_rows_and_values_string_set_one_row_dimension(self):
        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_two_row_dimensions(self):
        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(mdx)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3"})

    def test_execute_mdx_rows_and_values_string_set_include_empty(self):
        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[1])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[2])) \
            .to_mdx()

        elements_and_string_values = self.tm1.cubes.cells.execute_mdx_rows_and_values_string_set(
            mdx=mdx,
            exclude_empty_cells=False)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "d2e1", "d2e2", "d2e3", "d2e4", "String1", "String2", "String3", ""})

    def test_execute_mdx_rows_and_values_string_set_against_numeric_cells(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0]).head(10)) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1]).head(10)) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2]).head(10)) \
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
        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[2])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.string_dimension_names[1])) \
            .to_mdx()

        view_name = "some view"
        view = MDXView(cube_name=self.string_cube_name, view_name=view_name, MDX=mdx)
        self.tm1.cubes.views.update_or_create(view, private=False)

        elements_and_string_values = self.tm1.cubes.cells.execute_view_rows_and_values_string_set(
            cube_name=self.string_cube_name,
            view_name=view_name,
            private=False)

        self.assertEqual(
            set(elements_and_string_values),
            {"d1e1", "d1e2", "d1e3", "d1e4", "String1", "String2", "String3"})

    def test_execute_view(self):
        data = self.tm1.cubes.cells.execute_view(cube_name=self.cube_name, view_name=self.view_name, private=False)

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
        data = self.tm1.cubes.cells.execute_view(cube_name=self.cube_name, view_name=self.view_name, private=False,
                                                 top=3)
        self.assertEqual(len(data.keys()), 3)

    def test_execute_view_skip_contexts(self):
        view_name = self.prefix + "View_With_Titles"
        if not self.tm1.cubes.views.exists(cube_name=self.cube_name, view_name=view_name, private=False):
            view = NativeView(
                cube_name=self.cube_name,
                view_name=view_name,
                suppress_empty_columns=False,
                suppress_empty_rows=False)
            view.add_row(
                dimension_name=self.dimension_names[0],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[0],
                    expression='{[' + self.dimension_names[0] + '].[Element 1]}'))
            view.add_column(
                dimension_name=self.dimension_names[1],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[1],
                    expression='{[' + self.dimension_names[1] + '].[Element 1]}'))
            view.add_title(
                dimension_name=self.dimension_names[2],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[2],
                    expression='{[' + self.dimension_names[2] + '].Members}'),
                selection="Element 1")
            self.tm1.cubes.views.update_or_create(
                view=view,
                private=False)

        data = self.tm1.cubes.cells.execute_view(
            cube_name=self.cube_name,
            view_name=view_name,
            private=False,
            skip_contexts=True)

        self.assertEqual(len(data), 1)
        for coordinates, cell in data.items():
            self.assertEqual(len(coordinates), 2)
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[0]),
                self.dimension_names[0])
            self.assertEqual(
                Utils.dimension_name_from_element_unique_name(coordinates[1]),
                self.dimension_names[1])

    def test_execute_view_rows_and_values_one_dimension_on_rows(self):
        view_name = self.prefix + "MDX_View_With_One_Dim_On_Rows"
        if not self.tm1.cubes.views.exists(cube_name=self.cube_name, view_name=view_name, private=False):
            query = MdxBuilder.from_cube(self.cube_name)
            query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[0], "Element2")]))
            query = query.add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[1], "Element2"),
                Member.of(self.dimension_names[1], "Element3")]))
            query = query.where(Member.of(self.dimension_names[2], "Element1"))

            view = MDXView(cube_name=self.cube_name, view_name=view_name, MDX=query.to_mdx())
            self.tm1.cubes.views.update_or_create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=self.cube_name,
            view_name=view_name,
            private=False)

        self.assertEqual(len(data), 2)
        for row, cells in data.items():
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, self.dimension_names[0])
            self.assertEqual(len(cells), 3)

    def test_execute_view_rows_and_values_with_member_names(self):
        view_name = self.prefix + "MDX_View_With_Member_Names"
        if not self.tm1.cubes.views.exists(cube_name=self.cube_name, view_name=view_name, private=False):
            query = MdxBuilder.from_cube(self.cube_name)
            query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[0], "Element2")]))
            query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[2], "Element1"),
                Member.of(self.dimension_names[2], "Element2")]))
            query = query.add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[1], "Element2"),
                Member.of(self.dimension_names[1], "Element3")]))

            view = MDXView(cube_name=self.cube_name, view_name=view_name, MDX=query.to_mdx())
            self.tm1.cubes.views.update_or_create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=self.cube_name,
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
        view_name = self.prefix + "MDX_View_With_Two_Dim_On_Rows"
        if not self.tm1.cubes.views.exists(cube_name=self.cube_name, view_name=view_name, private=False):
            query = MdxBuilder.from_cube(self.cube_name)
            query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[0], "Element2")]))
            query = query.add_hierarchy_set_to_row_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[1], "Element2")]))
            query = query.add_hierarchy_set_to_column_axis(MdxHierarchySet.members([
                Member.of(self.dimension_names[2], "Element1"),
                Member.of(self.dimension_names[2], "Element2"),
                Member.of(self.dimension_names[2], "Element3")]))

            view = MDXView(cube_name=self.cube_name, view_name=view_name, MDX=query.to_mdx())
            self.tm1.cubes.views.update_or_create(view, False)

        data = self.tm1.cubes.cells.execute_view_rows_and_values(
            cube_name=self.cube_name,
            view_name=view_name,
            private=False)

        self.assertEqual(len(data), 4)
        for row, cells in data.items():
            self.assertEqual(len(row), 2)
            dimension = Utils.dimension_name_from_element_unique_name(row[0])
            self.assertEqual(dimension, self.dimension_names[0])
            dimension = Utils.dimension_name_from_element_unique_name(row[1])
            self.assertEqual(dimension, self.dimension_names[1])
            self.assertEqual(len(cells), 3)

    def test_execute_view_raw_skip_contexts(self):
        view_name = self.prefix + "View_With_Titles"
        if not self.tm1.cubes.views.exists(cube_name=self.cube_name, view_name=view_name, private=False):
            view = NativeView(
                cube_name=self.cube_name,
                view_name=view_name,
                suppress_empty_columns=False,
                suppress_empty_rows=False)
            view.add_row(
                dimension_name=self.dimension_names[0],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[0],
                    expression='{[' + self.dimension_names[0] + '].[Element 1]}'))
            view.add_column(
                dimension_name=self.dimension_names[1],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[1],
                    expression='{[' + self.dimension_names[1] + '].[Element 1]}'))
            view.add_title(
                dimension_name=self.dimension_names[2],
                subset=AnonymousSubset(
                    dimension_name=self.dimension_names[2],
                    expression='{[' + self.dimension_names[2] + '].Members}'),
                selection="Element 1")
            self.tm1.cubes.views.update_or_create(
                view=view,
                private=False)

        raw_response = self.tm1.cubes.cells.execute_view_raw(
            cube_name=self.cube_name,
            view_name=view_name,
            private=False,
            skip_contexts=True,
            member_properties=["UniqueName"])

        self.assertEqual(len(raw_response["Axes"]), 2)
        for axis in raw_response["Axes"]:
            dimension_on_axis = Utils.dimension_name_from_element_unique_name(
                axis["Tuples"][0]["Members"][0]["UniqueName"])
            self.assertNotEqual(dimension_on_axis, self.dimension_names[2])

    def test_execute_view_raw_with_member_properties_without_elem_properties(self):
        # Member properties and no element properties
        raw = self.tm1.cubes.cells.execute_view_raw(
            cube_name=self.cube_name,
            view_name=self.view_name,
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
            cube_name=self.cube_name,
            view_name=self.view_name,
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
            cube_name=self.cube_name,
            view_name=self.view_name,
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
            cube_name=self.cube_name,
            view_name=self.view_name,
            private=False,
            cell_properties=["Value", "RuleDerived"],
            elem_properties=["Name", "UniqueName", "Attributes/Attr1", "Attributes/Attr2"],
            top=5)
        self.assertEqual(len(raw["Cells"]), 5)

    def test_execute_view_values(self):
        cell_values = self.tm1.cubes.cells.execute_view_values(cube_name=self.cube_name, view_name=self.view_name,
                                                               private=False)

        # check type
        self.assertIsInstance(cell_values, list)

        # Check if total value is the same AND coordinates are the same. Handle None.
        self.assertEqual(self.total_value, sum(v for v in cell_values if v))

    def test_execute_view_csv(self):
        csv = self.tm1.cubes.cells.execute_view_csv(cube_name=self.cube_name, view_name=self.view_name, private=False)

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
            cube_name=self.cube_name,
            view_name=self.view_name,
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
            cube_name=self.cube_name,
            view_name=self.view_name,
            top=4,
            private=False)

        # check row count
        self.assertTrue(len(values) == 4)

        # check type
        self.assertIsInstance(values, CaseAndSpaceInsensitiveDict)

    @skip_if_no_pandas
    def test_execute_view_dataframe(self):
        df = self.tm1.cubes.cells.execute_view_dataframe(
            cube_name=self.cube_name,
            view_name=self.view_name,
            private=False)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates
        coordinates = {tuple(row)
                       for row
                       in df[[*self.dimension_names]].values}
        self.assertEqual(len(coordinates), len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        # check values
        values = df[["Value"]].values
        self.assertEqual(self.total_value, sum(values))

    @skip_if_no_pandas
    def test_execute_view_dataframe_with_top_argument(self):
        df = self.tm1.cubes.cells.execute_view_dataframe(
            cube_name=self.cube_name,
            view_name=self.view_name,
            top=2,
            private=False)

        # check row count
        self.assertTrue(len(df) == 2)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

    @skip_if_no_pandas
    def test_execute_view_dataframe_pivot_two_row_one_column_dimensions(self):
        view_name = self.prefix + "Pivot_two_row_one_column_dimensions"
        view = NativeView(
            cube_name=self.cube_name,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=self.dimension_names[0],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[0],
                expression='{ HEAD ( {[' + self.dimension_names[0] + '].Members}, 10) } }'))
        view.add_row(
            dimension_name=self.dimension_names[1],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[1],
                expression='{ HEAD ( { [' + self.dimension_names[1] + '].Members}, 10 ) }'))
        view.add_column(
            dimension_name=self.dimension_names[2],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[2],
                expression='{ HEAD ( {[' + self.dimension_names[2] + '].Members}, 10 ) }'))
        self.tm1.cubes.views.update_or_create(view, private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=self.cube_name,
            view_name=view_name)
        self.assertEqual((100, 10), pivot.shape)

    @skip_if_no_pandas
    def test_execute_view_dataframe_pivot_one_row_two_column_dimensions(self):
        view_name = self.prefix + "Pivot_one_row_two_column_dimensions"
        view = NativeView(
            cube_name=self.cube_name,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=self.dimension_names[0],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[0],
                expression='{ HEAD ( {[' + self.dimension_names[0] + '].Members}, 10) } }'))
        view.add_column(
            dimension_name=self.dimension_names[1],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[1],
                expression='{ HEAD ( { [' + self.dimension_names[1] + '].Members}, 10 ) }'))
        view.add_column(
            dimension_name=self.dimension_names[2],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[2],
                expression='{ HEAD ( {[' + self.dimension_names[2] + '].Members}, 10 ) }'))
        self.tm1.cubes.views.update_or_create(
            view=view,
            private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=self.cube_name,
            view_name=view_name)
        self.assertEqual((10, 100), pivot.shape)

    @skip_if_no_pandas
    def test_execute_view_dataframe_pivot_one_row_one_column_dimensions(self):
        view_name = self.prefix + "Pivot_one_row_one_column_dimensions"
        view = NativeView(
            cube_name=self.cube_name,
            view_name=view_name,
            suppress_empty_columns=False,
            suppress_empty_rows=False)
        view.add_row(
            dimension_name=self.dimension_names[0],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[0],
                expression='{ HEAD ( {[' + self.dimension_names[0] + '].Members}, 10) } }'))
        view.add_column(
            dimension_name=self.dimension_names[1],
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[1],
                expression='{ HEAD ( { [' + self.dimension_names[1] + '].Members}, 10 ) }'))
        view.add_title(
            dimension_name=self.dimension_names[2],
            selection="Element 1",
            subset=AnonymousSubset(
                dimension_name=self.dimension_names[2],
                elements=("Element 1",)))
        self.tm1.cubes.views.update_or_create(view, private=False)
        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=self.cube_name,
            view_name=view_name)
        self.assertEqual((10, 10), pivot.shape)

    @skip_if_no_pandas
    def test_execute_mdxview_dataframe_pivot(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.default_member(self.dimension_names[0])) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.default_member(self.dimension_names[1])) \
            .where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        view = MDXView(self.cube_name, self.prefix + "MDX_VIEW", mdx)
        self.tm1.cubes.views.update_or_create(
            view=view,
            private=False)

        pivot = self.tm1.cubes.cells.execute_view_dataframe_pivot(
            cube_name=self.cube_name,
            view_name=view.name,
            private=False)
        self.assertEqual((1, 1), pivot.shape)

        self.tm1.cubes.views.delete(
            cube_name=self.cube_name,
            view_name=view.name,
            private=False)

    def test_execute_view_cellcount(self):
        cell_count = self.tm1.cubes.cells.execute_view_cellcount(
            cube_name=self.cube_name,
            view_name=self.view_name,
            private=False)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_ui_array(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        self.tm1.cubes.cells.execute_mdx_ui_array(mdx=mdx)

    def test_execute_view_ui_array(self):
        self.tm1.cubes.cells.execute_view_ui_array(
            cube_name=self.cube_name,
            view_name=self.view_name,
            private=False)

    def test_execute_mdx_ui_dygraph(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .rows_non_empty() \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[0], self.dimension_names[0])) \
            .add_hierarchy_set_to_row_axis(
            MdxHierarchySet.all_members(self.dimension_names[1], self.dimension_names[1])) \
            .columns_non_empty() \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.all_members(self.dimension_names[2], self.dimension_names[2])) \
            .to_mdx()

        self.tm1.cubes.cells.execute_mdx_ui_dygraph(mdx=mdx)

    def test_execute_view_ui_dygraph(self):
        self.tm1.cubes.cells.execute_view_ui_dygraph(
            cube_name=self.cube_name,
            view_name=self.view_name,
            private=False)

    def test_write_values_through_cellset(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "element2"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "element2"))) \
            .where(Member.of(self.dimension_names[2], "element2")) \
            .to_mdx()

        self.tm1.cubes.cells.write_values_through_cellset(mdx, (1.5,))

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertEqual(values[0], 1.5)

    def test_write_values_through_cellset_deactivate_transaction_log(self):
        query = MdxBuilder.from_cube(self.cube_name)
        query = query.add_hierarchy_set_to_row_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[0], "element2")))
        query = query.add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.dimension_names[1], "element2")))
        query = query.where(Member.of(self.dimension_names[2], "element2"))

        self.tm1.cubes.cells.write_values_through_cellset(query.to_mdx(), (1.5,), deactivate_transaction_log=True)

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(query.to_mdx())
        self.assertEqual(values[0], 1.5)

        self.assertFalse(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_write_values_through_cellset_deactivate_transaction_log_reactivate_transaction_log(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "element2"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "element2"))) \
            .where(Member.of(self.dimension_names[2], "element2")) \
            .to_mdx()

        self.tm1.cubes.cells.write_values_through_cellset(
            mdx,
            (1.5,),
            deactivate_transaction_log=True,
            reactivate_transaction_log=True)

        # check value on coordinate in cube
        values = self.tm1.cubes.cells.execute_mdx_values(mdx)

        self.assertEqual(values[0], 1.5)
        self.assertTrue(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_deactivate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="YES",
                                         cube_name="}CubeProperties",
                                         element_tuple=(self.cube_name, "Logging"))
        self.tm1.cubes.cells.deactivate_transactionlog(self.cube_name)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(self.cube_name))
        self.assertEqual("NO", value.upper())

    def test_activate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="NO",
                                         cube_name="}CubeProperties",
                                         element_tuple=(self.cube_name, "Logging"))
        self.tm1.cubes.cells.activate_transactionlog(self.cube_name)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(self.cube_name))
        self.assertEqual("YES", value.upper())

    def test_read_write_with_custom_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(self.string_cube_name, {coordinates: self.latin_1_encoded_text},
                                          encoding="latin-1")

        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertEqual(self.latin_1_encoded_text, values[0])

    def test_read_write_with_custom_encoding_fail_response_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(self.string_cube_name, {coordinates: self.latin_1_encoded_text},
                                          encoding="latin-1")

        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx)

        self.assertNotEqual(self.latin_1_encoded_text, values[0])

    def test_read_write_with_custom_encoding_fail_request_encoding(self):
        coordinates = ("d1e1", "d2e2", "d3e3")
        self.tm1.cubes.cells.write_values(self.string_cube_name, {coordinates: self.latin_1_encoded_text})

        mdx = MdxBuilder.from_cube(self.string_cube_name) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[0], coordinates[0]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[1], coordinates[1]))) \
            .add_hierarchy_set_to_column_axis(
            MdxHierarchySet.member(Member.of(self.string_dimension_names[2], coordinates[2]))) \
            .to_mdx()

        values = self.tm1.cubes.cells.execute_mdx_values(mdx=mdx, encoding="latin-1")
        self.assertNotEqual(self.latin_1_encoded_text, values[0])

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_happy_case(self):
        cells = {("Element17", "Element21", "Element15"): 1}
        self.tm1.cells.write_values(self.cube_name, cells)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element17"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element21"))) \
            .where(Member.of(self.dimension_names[2], "Element15")) \
            .to_mdx()

        self.tm1.cells.clear_with_mdx(cube=self.cube_name, mdx=mdx)

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_all_on_axis0(self):
        cells = {("Element19", "Element11", "Element31"): 1}
        self.tm1.cells.write_values(self.cube_name, cells)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element19"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element11"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[2], "Element31"))) \
            .to_mdx()
        self.tm1.cells.clear_with_mdx(cube=self.cube_name, mdx=mdx)

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_happy_case(self):
        cells = {("Element12", "Element17", "Element32"): 1}
        self.tm1.cells.write_values(self.cube_name, cells)

        kwargs = {
            self.dimension_names[0]: f"[{self.dimension_names[0]}].[Element12]",
            self.dimension_names[1]: f"{{[{self.dimension_names[1]}].[Element17]}}",
            self.dimension_names[2]: f"[{self.dimension_names[2]}].[Element32]"
        }
        self.tm1.cells.clear(cube=self.cube_name, **kwargs)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element12"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element17"))) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.member(Member.of(self.dimension_names[2], "Element32"))) \
            .to_mdx()

        value = self.tm1.cells.execute_mdx_values(mdx=mdx)[0]
        self.assertEqual(value, None)

    @skip_if_insufficient_version(version="11.7")
    def test_clear_invalid_element_name(self):

        with self.assertRaises(TM1pyException) as e:
            kwargs = {
                self.dimension_names[0]: f"[{self.dimension_names[0]}].[Element12]",
                self.dimension_names[1]: f"[{self.dimension_names[1]}].[Element17]",
                self.dimension_names[2]: f"[{self.dimension_names[2]}].[NotExistingElement]"
            }
            self.tm1.cells.clear(cube=self.cube_name, **kwargs)

        self.assertIn(
            '\\"NotExistingElement\\" :',
            str(e.exception.message))

    @skip_if_insufficient_version(version="11.7")
    def test_clear_with_mdx_invalid_query(self):
        with self.assertRaises(TM1pyException) as e:
            mdx = f"""
            SELECT
            {{[{self.dimension_names[0]}].[NotExistingElement]}} ON 0
            FROM [{self.cube_name}]
            """
            self.tm1.cells.clear_with_mdx(cube=self.cube_name, mdx=mdx)

        self.assertIn(
            '\\"NotExistingElement\\" :',
            str(e.exception.message))

    def test_clear_with_mdx_unsupported_version(self):

        with self.assertRaises(TM1pyVersionException) as e:
            mdx = MdxBuilder.from_cube(self.cube_name) \
                .add_hierarchy_set_to_column_axis(
                MdxHierarchySet.member(Member.of(self.dimension_names[0], "Element19"))) \
                .add_hierarchy_set_to_column_axis(
                MdxHierarchySet.member(Member.of(self.dimension_names[1], "Element11"))) \
                .add_hierarchy_set_to_column_axis(
                MdxHierarchySet.member(Member.of(self.dimension_names[2], "Element31"))) \
                .to_mdx()

            # This needs to be rethought as may influence other tests
            self.tm1._tm1_rest._version = "11.2.00000.27"

            self.tm1.cells.clear_with_mdx(cube=self.cube_name, mdx=mdx)

        self.assertEqual(
            str(e.exception),
            str(TM1pyVersionException(function="clear_with_mdx", required_version="11.7")))

    def test_execute_mdx_with_skip(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.dimension_names[0]).head(2)) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.dimension_names[1]).head(2)) \
            .where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        cells = self.tm1.cubes.cells.execute_mdx(mdx=mdx, skip=2)
        self.assertEqual(len(cells), 2)

        elements = element_names_from_element_unique_names(list(cells.keys())[0])
        self.assertEqual(elements, ("Element 2", "Element 1", "Element 1"))

        elements = element_names_from_element_unique_names(list(cells.keys())[1])
        self.assertEqual(elements, ("Element 2", "Element 2", "Element 1"))

    def test_execute_mdx_with_top_skip(self):
        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_hierarchy_set_to_row_axis(MdxHierarchySet.tm1_subset_all(self.dimension_names[0]).head(2)) \
            .add_hierarchy_set_to_column_axis(MdxHierarchySet.tm1_subset_all(self.dimension_names[1]).head(2)) \
            .where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        cells = self.tm1.cubes.cells.execute_mdx(mdx=mdx, top=1, skip=2)
        self.assertEqual(len(cells), 1)

        elements = element_names_from_element_unique_names(list(cells.keys())[0])
        self.assertEqual(elements, ("Element 2", "Element 1", "Element 1"))

    def test_transaction_log_is_active_false(self):
        self.tm1.cells.deactivate_transactionlog(self.cube_name)

        self.assertFalse(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_transaction_log_is_active_true(self):
        self.tm1.cells.activate_transactionlog(self.cube_name)

        self.assertTrue(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_manage_transaction_log_deactivate_reactivate(self):
        self.tm1.cubes.cells.write_values(
            self.cube_name,
            self.cellset,
            deactivate_transaction_log=True,
            reactivate_transaction_log=True)

        self.assertTrue(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_manage_transaction_log_not_deactivate_not_reactivate(self):
        pre_state = self.tm1.cells.transaction_log_is_active(self.cube_name)

        self.tm1.cubes.cells.write_values(
            self.cube_name,
            self.cellset,
            deactivate_transaction_log=False,
            reactivate_transaction_log=False)

        self.assertEqual(pre_state, self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_manage_transaction_log_deactivate_not_reactivate(self):
        self.tm1.cubes.cells.write_values(
            self.cube_name,
            self.cellset,
            deactivate_transaction_log=True,
            reactivate_transaction_log=False)

        self.assertFalse(self.tm1.cells.transaction_log_is_active(self.cube_name))

    def test_write_values_with_sandbox(self):
        self.tm1.cubes.cells.write_values(
            self.cube_name,
            {("Element1", "Element1", "Element1"): 7},
            sandbox_name=self.sandbox_name)

        mdx = MdxBuilder.from_cube(self.cube_name).add_member_tuple_to_columns(
            Member.of(self.dimension_names[0], "Element1"),
            Member.of(self.dimension_names[1], "Element1"),
            Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        values = self.tm1.cells.execute_mdx_values(mdx, sandbox_name=self.sandbox_name)
        self.assertEqual(7, values[0])

    def test_write_values_through_cellset_with_sandbox(self):
        mdx = MdxBuilder.from_cube(self.cube_name).add_member_tuple_to_columns(
            Member.of(self.dimension_names[0], "Element1"),
            Member.of(self.dimension_names[1], "Element1"),
            Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        self.tm1.cubes.cells.write_values_through_cellset(
            mdx=mdx,
            values=[8],
            sandbox_name=self.sandbox_name)

        values = self.tm1.cells.execute_mdx_values(mdx, sandbox_name=self.sandbox_name)
        self.assertEqual(8, values[0])

    def test_execute_mdx_with_sandbox(self):
        self.tm1.cubes.cells.write_values(
            self.cube_name,
            {("Element1", "Element1", "Element1"): 12},
            sandbox_name=self.sandbox_name)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_member_tuple_to_columns(Member.of(self.dimension_names[0], "Element1")) \
            .add_member_tuple_to_rows(Member.of(self.dimension_names[1], "Element1")) \
            .add_member_to_where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        result = self.tm1.cells.execute_mdx(mdx, sandbox_name=self.sandbox_name)
        self.assertEqual(1, len(result))
        for coordinates, cell in result.items():
            self.assertEqual(12, cell["Value"])

    def test_execute_mdx_rows_and_values_with_sandbox(self):
        self.tm1.cubes.cells.write_values(
            self.cube_name,
            {("Element1", "Element1", "Element1"): 118},
            sandbox_name=self.sandbox_name)

        mdx = MdxBuilder.from_cube(self.cube_name) \
            .add_member_tuple_to_columns(Member.of(self.dimension_names[0], "Element1")) \
            .add_member_tuple_to_rows(Member.of(self.dimension_names[1], "Element1")) \
            .add_member_to_where(Member.of(self.dimension_names[2], "Element1")) \
            .to_mdx()

        result = self.tm1.cells.execute_mdx_rows_and_values(mdx, sandbox_name=self.sandbox_name)
        self.assertEqual(1, len(result))
        for rows, values in result.items():
            self.assertEqual(118, values[0])

    def test_get_value(self):
        value = self.tm1.cells.get_value(
            cube_name=self.cube_name,
            element_string="Element1,Element1,Element1")

        self.assertEqual(1, value)

    def test_get_value_other_hierarchy_in_attribute_cube(self):
        value = self.tm1.cells.get_value(
            cube_name='}ElementAttributes_' + self.dimension_with_hierarchies_name,
            element_string=f'Hierarchy2::Cons1,ea2')

        self.assertEqual('ABC', value)

    def test_trace_cell_calculation_no_depth_iterable(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements=["Element1", "Element1", "Element1"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_shallow_depth_iterable(self):
        shallow_depth = 1
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements=["Element3", "Element1", "Element1"],
            depth=shallow_depth)

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')
        components = result["Components"]

        self.assertNotIn("Components", components)

    def test_trace_cell_calculation_deep_depth_iterable(self):
        shallow_depth = 2
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements=["Element3", "Element1", "Element1"],
            depth=shallow_depth)

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')
        components = result["Components"]
        for _ in range(shallow_depth - 1):
            components = components[0]["Components"]

        self.assertNotIn("Components", components)

    def test_trace_cell_calculation_dimensions_iterable(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements=["Element1", "Element1", "Element1"],
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_no_depth_string(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1")

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_shallow_depth_string(self):
        shallow_depth = 2

        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="Element3,Element1,Element1",
            depth=shallow_depth)

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')
        components = result["Components"]
        for _ in range(shallow_depth - 1):
            components = components[0]["Components"]

        self.assertNotIn("Components", components)

    def test_trace_cell_calculation_deep_depth_string(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1",
            depth=25)

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_dimensions_string(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_dimensions_string_hierarchy(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_cell_calculation_dimensions_string_multi_hierarchy(self):
        result = self.tm1.cells.trace_cell_calculation(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1 && TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.CalculationComponent')

    def test_trace_feeders_string(self):
        result = self.tm1.cells.trace_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1")

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.FeederTrace')

    def test_trace_feeders_dimensions_string(self):
        result = self.tm1.cells.trace_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.FeederTrace')

    def test_trace_feeders_dimensions_string_hierarchy(self):
        result = self.tm1.cells.trace_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.FeederTrace')

    def test_trace_feeders_dimensions_string_multi_hierarchy(self):
        result = self.tm1.cells.trace_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1 && TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#ibm.tm1.api.v1.FeederTrace')

    def test_check_feeders_string(self):
        result = self.tm1.cells.check_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1")

        self.assertEqual(result['@odata.context'], '../$metadata#Collection(ibm.tm1.api.v1.FedCellDescriptor)')

    def test_check_feeders_dimensions_string(self):
        result = self.tm1.cells.check_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="Element1,Element1,Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#Collection(ibm.tm1.api.v1.FedCellDescriptor)')

    def test_check_feeders_dimensions_string_hierarchy(self):
        result = self.tm1.cells.check_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#Collection(ibm.tm1.api.v1.FedCellDescriptor)')

    def test_check_feeders_dimensions_string_multi_hierarchy(self):
        result = self.tm1.cells.check_cell_feeders(
            cube_name=self.cube_with_rules_name,
            elements="TM1py_Tests_Cell_Dimension1::Element1 && TM1py_Tests_Cell_Dimension1::Element1,"
                     "TM1py_Tests_Cell_Dimension2::Element3,"
                     "TM1py_Tests_Cell_Dimension3::Element1",
            dimensions=["TM1py_Tests_Cell_Dimension1", "TM1py_Tests_Cell_Dimension2", "TM1py_Tests_Cell_Dimension3"])

        self.assertEqual(result['@odata.context'], '../$metadata#Collection(ibm.tm1.api.v1.FedCellDescriptor)')

    # Delete Cube and Dimensions
    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cls.cube_name)
        cls.remove_string_cube()
        cls.remove_cube_with_rules()
        cls.remove_cube_with_consolidations()
        cls.remove_cube_with_five_dimensions()
        for dimension_name in cls.dimension_names:
            cls.tm1.dimensions.delete(dimension_name)
        cls.remove_assets_for_relative_proportional_spread()

        if cls.tm1.sandboxes.exists(cls.sandbox_name):
            cls.tm1.sandboxes.delete(cls.sandbox_name)

        cls.tm1.dimensions.delete(cls.dimension_with_hierarchies_name)

        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
