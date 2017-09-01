import random
import unittest

from TM1py.Objects import Cube, Dimension, Element, Hierarchy
from TM1py.Services import TM1Service
from TM1py.Utils import Utils

from .config import test_config


# Hard coded stuff
cube_name = 'TM1py_unittest_cube'
dimension_names = ['TM1py_unittest_dimension1',
                   'TM1py_unittest_dimension2',
                   'TM1py_unittest_dimension3']


class TestDataMethods(unittest.TestCase):
    # Connection to TM1
    tm1 = TM1Service(**test_config)
    # generate random coordinates
    target_coordinates = list(zip(('Element ' + str(random.randint(1, 1000)) for i in range(100)),
                                  ('Element ' + str(random.randint(1, 1000)) for j in range(100)),
                                  ('Element ' + str(random.randint(1, 1000)) for k in range(100))))
    # Sum of all the values that we write in the cube. serves as a checksum
    total_value = 0

    def test1_write(self):
        # Write data into cube
        cellset = {}
        for element1, element2, element3 in TestDataMethods.target_coordinates:
            value = random.randint(1, 1000)
            cellset[(element1, element2, element3)] = value
            # update the checksum
            TestDataMethods.total_value += value
        self.tm1.cubes.cells.write_values(cube_name, cellset)

    def test2_read(self):
        # Define MDX Query that gets full cube content
        mdx = "SELECT " \
              "NON EMPTY [" + dimension_names[0] + "].Members * [" + dimension_names[1] + "].Members ON ROWS," \
              "NON EMPTY [" + dimension_names[2] + "].MEMBERS ON COLUMNS " \
              "FROM [" + cube_name + "]"
        data = self.tm1.cubes.cells.execute_mdx(mdx)
        # Check if total value is the same AND coordinates are the same
        check_value = 0
        for coordinates, value in data.items():
            # grid can have null values in cells as rows and columns are populated with elements
            if value['Value']:
                # extract the element name from the element unique name
                element_names = Utils.element_names_from_element_unqiue_names(coordinates)
                self.assertIn(element_names, TestDataMethods.target_coordinates)
                check_value += value['Value']
        # Check the check-sum
        self.assertEqual(check_value, TestDataMethods.total_value)

    #TODO write test for get_value function in CellService

    # Setup Cubes, Dimensions and Subsets
    @classmethod
    def setup_class(cls):
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

    # Delete Cube and Dimensions
    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(cube_name)
        for dimension_name in dimension_names:
            cls.tm1.dimensions.delete(dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
