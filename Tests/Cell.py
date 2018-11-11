import configparser
import os
import random
import types
import unittest
import uuid

import pandas as pd

from TM1py.Objects import Cube, Dimension, Element, Hierarchy, NativeView, AnonymousSubset, ElementAttribute
from TM1py.Services import TM1Service
from TM1py.Utils import Utils

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

# Hard coded stuff
CUBE_NAME = 'TM1py_unittest_cube'
VIEW_NAME = str(uuid.uuid4())
DIMENSION_NAMES = [
    'TM1py_unittest_dimension1',
    'TM1py_unittest_dimension2',
    'TM1py_unittest_dimension3']


class TestDataMethods(unittest.TestCase):

    # Setup Cubes, Dimensions and Subsets
    @classmethod
    def setup_class(cls):
        # Connection to TM1
        cls.tm1 = TM1Service(**config['tm1srv01'])

        # generate random coordinates
        cls.target_coordinates = list(zip(('Element ' + str(random.randint(1, 1000)) for _ in range(100)),
                                          ('Element ' + str(random.randint(1, 1000)) for _ in range(100)),
                                          ('Element ' + str(random.randint(1, 1000)) for _ in range(100))))

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
            if not cls.tm1.dimensions.exists(dimension.name):
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
        view = NativeView(cube_name=CUBE_NAME, view_name=VIEW_NAME,
                          suppress_empty_columns=True, suppress_empty_rows=True)
        subset = AnonymousSubset(dimension_name=DIMENSION_NAMES[0],
                                 expression='{[' + DIMENSION_NAMES[0] + '].Members}')
        view.add_row(dimension_name=DIMENSION_NAMES[0], subset=subset)
        subset = AnonymousSubset(dimension_name=DIMENSION_NAMES[1],
                                 expression='{[' + DIMENSION_NAMES[1] + '].Members}')
        view.add_row(dimension_name=DIMENSION_NAMES[1], subset=subset)
        subset = AnonymousSubset(dimension_name=DIMENSION_NAMES[2],
                                 expression='{[' + DIMENSION_NAMES[2] + '].Members}')
        view.add_column(dimension_name=DIMENSION_NAMES[2], subset=subset)
        cls.tm1.cubes.views.create(view, private=False)

        # Sum of all the values that we write in the cube. serves as a checksum
        cls.total_value = 0

        # cellset of data that shall be written
        cls.cellset = {}
        for element1, element2, element3 in cls.target_coordinates:
            value = random.randint(1, 1000)
            cls.cellset[(element1, element2, element3)] = value
            # update the checksum
            cls.total_value += value

        # Fill cube with values
        cls.tm1.cubes.cells.write_values(CUBE_NAME, cls.cellset)

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
        mdx = "WITH MEMBER[{}].[{}] AS 2 " \
              "SELECT[{}].MEMBERS ON ROWS, " \
              "{{[{}].[{}]}} ON COLUMNS " \
              "FROM[{}] " \
              "WHERE([{}].DefaultMember)".format(DIMENSION_NAMES[1], "Calculated Member", DIMENSION_NAMES[0],
                                                 DIMENSION_NAMES[1], "Calculated Member", CUBE_NAME, DIMENSION_NAMES[2])

        data = self.tm1.cubes.cells.execute_mdx(mdx, cell_properties=["Value", "Ordinal"])
        self.assertEqual(1000, len(data))
        self.assertEqual(2000, sum(v["Value"] for v in data.values()))
        self.assertEqual(
            sum(range(0, 1000)),
            sum(v["Ordinal"] for v in data.values()))

    def test_execute_mdx_raw_with_member_properties_with_elem_properties(self):
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
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
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
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
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
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
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
        cell_values = self.tm1.cubes.cells.execute_mdx_values(mdx)
        self.assertIsInstance(
            cell_values,
            types.GeneratorType)
        # Check if total value is the same AND coordinates are the same. Handle None.
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
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
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
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
        df = self.tm1.cubes.cells.execute_mdx_dataframe(mdx)

        # check type
        self.assertIsInstance(df, pd.DataFrame)

        # check coordinates in df are equal to target coordinates
        coordinates = {tuple(row)
                       for row
                       in df[[*DIMENSION_NAMES]].values}
        self.assertEqual(len(coordinates),
                         len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        # check if total values are equal
        values = df[["Value"]].values
        self.assertEqual(self.total_value,
                         sum(values))

    def test_execute_mdx_cellcount(self):
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
        cell_count = self.tm1.cubes.cells.execute_mdx_cellcount(mdx)
        self.assertGreater(cell_count, 1000)

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
        df = self.tm1.cubes.cells.execute_view_dataframe(cube_name=CUBE_NAME, view_name=VIEW_NAME, private=False)

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

    def test_execute_view_cellcount(self):
        cell_count = self.tm1.cubes.cells.execute_view_cellcount(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)
        self.assertGreater(cell_count, 1000)

    def test_execute_mdx_ui_array(self):
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
        self.tm1.cubes.cells.execute_mdx_ui_array(mdx=mdx)

    def test_execute_view_ui_array(self):
        self.tm1.cubes.cells.execute_view_ui_array(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            private=False)

    def test_execute_mdx_ui_dygraph(self):
        mdx = "SELECT " \
              "NON EMPTY [" + DIMENSION_NAMES[0] + "].Members * [" + DIMENSION_NAMES[1] + "].Members ON ROWS," \
              "NON EMPTY [" + DIMENSION_NAMES[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + CUBE_NAME + "]"
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

    # Delete Cube and Dimensions
    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(CUBE_NAME)
        for dimension_name in DIMENSION_NAMES:
            cls.tm1.dimensions.delete(dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
