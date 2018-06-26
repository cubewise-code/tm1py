import random
import os
import unittest
import uuid
import configparser

from TM1py.Objects import Cube, Dimension, Element, Hierarchy, NativeView, AnonymousSubset
from TM1py.Services import TM1Service
from TM1py.Utils import Utils

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


# Hard coded stuff
cube_name = 'TM1py_unittest_cube'
view_name = str(uuid.uuid4())
dimension_names = ['TM1py_unittest_dimension1',
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
        for i in range(3):
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_names[i], dimension_names[i], elements)
            dimension = Dimension(dimension_names[i], [hierarchy])
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(cube_name, dimension_names)
        if not cls.tm1.cubes.exists(cube_name):
            cls.tm1.cubes.create(cube)

        # Build cube view
        view = NativeView(cube_name=cube_name, view_name=view_name,
                          suppress_empty_columns=True, suppress_empty_rows=True)
        subset = AnonymousSubset(dimension_name=dimension_names[0],
                                 expression='{[' + dimension_names[0] + '].Members}')
        view.add_row(dimension_name=dimension_names[0], subset=subset)
        subset = AnonymousSubset(dimension_name=dimension_names[1],
                                 expression='{[' + dimension_names[1] + '].Members}')
        view.add_row(dimension_name=dimension_names[1], subset=subset)
        subset = AnonymousSubset(dimension_name=dimension_names[2],
                                 expression='{[' + dimension_names[2] + '].Members}')
        view.add_column(dimension_name=dimension_names[2], subset=subset)
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

    def test01_write_value(self):
        self.tm1.cubes.cells.write_value(1, cube_name, ('element1', 'ELEMENT 2', 'EleMent  3'))

    def test02_get_value(self):
        # clear data in cube
        self.tm1.processes.execute_ti_code(lines_prolog="CubeClearData('{}');".format(cube_name))
        self.tm1.cubes.cells.write_value(-1, cube_name, ('Element1', 'Element 2', 'Element 3'))
        value = self.tm1.cubes.cells.get_value(cube_name, 'Element1,EleMent2,ELEMENT  3')
        self.assertEqual(value, -1)
        # clear data in cube
        self.tm1.processes.execute_ti_code(lines_prolog="CubeClearData('{}');".format(cube_name))

    def test03_write_values(self):
        self.tm1.cubes.cells.write_values(cube_name, self.cellset)

    def test04_execute_mdx(self):
        # Define MDX Query that gets full cube content
        mdx = "SELECT " \
              "NON EMPTY [" + dimension_names[0] + "].Members * [" + dimension_names[1] + "].Members ON ROWS," \
              "NON EMPTY [" + dimension_names[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + cube_name + "]"
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same. Handle None
        self.assertEqual(self.total_value,
                         sum([v["Value"] for v in data.values() if v["Value"]]))

        # Define MDX Query with calculated MEMBER
        mdx = "WITH MEMBER[{}].[{}] AS 2 " \
              "SELECT[{}].MEMBERS ON ROWS, " \
              "NON EMPTY {{[{}].[{}]}} ON COLUMNS " \
              "FROM[{}] " \
              "WHERE([{}].DefaultMember)".format(dimension_names[1], "Calculated Member", dimension_names[0],
                                                 dimension_names[1], "Calculated Member", cube_name, dimension_names[2])

        data = self.tm1.cubes.cells.execute_mdx(mdx)
        self.assertEqual(1000, len(data))
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        self.assertEqual(2000, sum(v["Value"] for v in data.values()))
        self.assertEqual(
            sum(range(0, 1000)),
            sum(v["Ordinal"] for v in data.values()))

    def test05_execute_mdx_cell_values_only(self):
        mdx = "SELECT " \
              "NON EMPTY [" + dimension_names[0] + "].Members * [" + dimension_names[1] + "].Members ON ROWS," \
              "NON EMPTY [" + dimension_names[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + cube_name + "]"

        cell_values = self.tm1.cubes.cells.execute_mdx_get_values_only(mdx)

        # Check if total value is the same AND coordinates are the same. Handle None.
        self.assertEqual(self.total_value,
                         sum([v for v in cell_values if v]))

        # Define MDX Query with calculated MEMBER
        mdx = "WITH MEMBER[{}].[{}] AS 2 " \
              "SELECT[{}].MEMBERS ON ROWS, " \
              "NON EMPTY {{[{}].[{}]}} ON COLUMNS " \
              "FROM[{}] " \
              "WHERE([{}].DefaultMember)".format(dimension_names[1], "Calculated Member", dimension_names[0],
                                                 dimension_names[1], "Calculated Member", cube_name, dimension_names[2])

        data = self.tm1.cubes.cells.execute_mdx_get_values_only(mdx)
        self.assertEqual(1000, len(list(data)))
        data = self.tm1.cubes.cells.execute_mdx_get_values_only(mdx)
        self.assertEqual(2000, sum(data))

    def test06_execute_mdx_get_csv(self):
        mdx = "SELECT " \
              "NON EMPTY [" + dimension_names[0] + "].Members * [" + dimension_names[1] + "].Members ON ROWS," \
              "NON EMPTY [" + dimension_names[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + cube_name + "]"
        content = self.tm1.cubes.cells.execute_mdx_get_csv(mdx)

        records = content.split('\r\n')[1:]
        coordinates = {tuple(record.split(',')[0:3]) for record in records if record != '' and records[4] != 0}
        self.assertEqual(len(coordinates), len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        values = [float(record.split(',')[3]) for record in records if record != '']
        self.assertEqual(self.total_value, sum(values))

    def test07_execute_mdx_get_dataframe(self):
        mdx = "SELECT " \
              "NON EMPTY [" + dimension_names[0] + "].Members * [" + dimension_names[1] + "].Members ON ROWS," \
              "NON EMPTY [" + dimension_names[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + cube_name + "]"
        df = self.tm1.cubes.cells.execute_mdx_get_dataframe(mdx)

        coordinates = {tuple(row)
                       for row
                       in df[[*dimension_names]].values}
        self.assertEqual(len(coordinates), len(self.target_coordinates))
        self.assertTrue(coordinates.issubset(self.target_coordinates))

        values = df[["Value"]].values
        self.assertEqual(self.total_value, sum(values))

    def test08_execute_view(self):
        data = self.tm1.cubes.cells.execute_view(cube_name, view_name, private=False)
        # Check if total value is the same AND coordinates are the same
        check_value = 0
        for coordinates, value in data.items():
            # grid can have null values in cells as rows and columns are populated with elements
            if value['Value']:
                # extract the element name from the element unique name
                element_names = Utils.element_names_from_element_unqiue_names(coordinates)
                self.assertIn(element_names, self.target_coordinates)
                check_value += value['Value']
        # Check the check-sum
        self.assertEqual(check_value, self.total_value)

    def test09_execute_view(self):
        data = self.tm1.cubes.cells.execute_view(cube_name, view_name, private=False, top=3)
        self.assertEqual(len(data.keys()), 3)

    def test10_write_values_through_cellset(self):
        mdx_skeleton = "SELECT {} ON ROWS, {} ON COLUMNS FROM {} WHERE ({})"
        mdx = mdx_skeleton.format(
            "{{[{}].[{}]}}".format(dimension_names[0], "element2"),
            "{{[{}].[{}]}}".format(dimension_names[1], "element2"),
            cube_name,
            "[{}].[{}]".format(dimension_names[2], "element2"),
        )
        self.tm1.cubes.cells.write_values_through_cellset(mdx, (1,))

    def test11_deactivate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="YES", cube_name="}CubeProperties",
                                         element_tuple=(cube_name, "Logging"))
        self.tm1.cubes.cells.deactivate_transactionlog(cube_name)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(cube_name))
        self.assertEqual("NO", value.upper())

    def test12_activate_transaction_log(self):
        self.tm1.cubes.cells.write_value(value="NO", cube_name="}CubeProperties",
                                         element_tuple=(cube_name, "Logging"))
        self.tm1.cubes.cells.activate_transactionlog(cube_name)
        value = self.tm1.cubes.cells.get_value("}CubeProperties", "{},LOGGING".format(cube_name))
        self.assertEqual("YES", value.upper())

    # Delete Cube and Dimensions
    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(cube_name)
        for dimension_name in dimension_names:
            cls.tm1.dimensions.delete(dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
