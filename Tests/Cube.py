import configparser
import os
import unittest
import uuid

from TM1py import Element, Hierarchy, Dimension
from TM1py.Objects import Cube
from TM1py.Objects import Rules
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

PREFIX = "TM1py_Tests_Cube_"


class TestCubeMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])
        cls.cube_name = PREFIX + "some_name"
        cls.dimension_names = [
            PREFIX + "dimension1",
            PREFIX + "dimension2",
            PREFIX + "dimension3"]

        # Build Dimensions
        for dimension_name in cls.dimension_names:
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements)
            dimension = Dimension(dimension_name, [hierarchy])
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(cls.cube_name, cls.dimension_names)
        if not cls.tm1.cubes.exists(cls.cube_name):
            cls.tm1.cubes.create(cube)
        c = Cube(cls.cube_name, dimensions=cls.dimension_names, rules=Rules(''))
        if cls.tm1.cubes.exists(c.name):
            cls.tm1.cubes.delete(c.name)
        cls.tm1.cubes.create(c)

    def test_get_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        self.assertIsInstance(c, Cube)
        self.assertEqual(c.dimensions, self.dimension_names)

        cubes = self.tm1.cubes.get_all()
        control_cubes = self.tm1.cubes.get_control_cubes()
        model_cubes = self.tm1.cubes.get_model_cubes()
        self.assertEqual(len(cubes), len(control_cubes + model_cubes))

    def test_update_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        c.rules = Rules("SKIPCHECK;\nFEEDERS;")
        self.tm1.cubes.update(c)
        # test if rule was actually updated
        c = self.tm1.cubes.get(self.cube_name)
        self.assertEqual(c.rules.text, "SKIPCHECK;\nFEEDERS;")
        self.assertTrue(c.skipcheck)

    def test_get_control_cubes(self):
        control_cubes = self.tm1.cubes.get_control_cubes()
        self.assertGreater(len(control_cubes), 0)
        for cube in control_cubes:
            self.assertTrue(cube.name.startswith("}"))

    def test_get_model_cubes(self):
        model_cubes = self.tm1.cubes.get_model_cubes()
        self.assertGreater(len(model_cubes), 0)
        for cube in model_cubes:
            self.assertFalse(cube.name.startswith("}"))

    def test_get_dimension_names(self):
        dimension_names = self.tm1.cubes.get_dimension_names(self.cube_name)
        self.assertEqual(dimension_names, self.dimension_names)

    def test_get_random_intersection(self):
        intersection1 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=False)
        intersection2 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=False)
        self.assertNotEqual(intersection1, intersection2)
        intersection1 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=True)
        intersection2 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=True)
        self.assertNotEqual(intersection1, intersection2)

    def test_exists(self):
        self.assertTrue(self.tm1.cubes.exists(self.cube_name))
        self.assertFalse(self.tm1.cubes.exists(uuid.uuid4()))

    def test_create_delete_cube(self):
        cube_name = PREFIX + "Some_Other_Name"
        dimension_names = self.tm1.dimensions.get_all_names()[0:2]
        cube = Cube(cube_name, dimension_names)

        all_cubes_before = self.tm1.cubes.get_all_names()
        self.tm1.cubes.create(cube)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(
            len(all_cubes_before) + 1,
            len(all_cubes_after))
        self.assertEqual(
            self.tm1.cubes.get_dimension_names(cube_name),
            dimension_names)

        all_cubes_before = self.tm1.cubes.get_all_names()
        self.tm1.cubes.delete(cube_name)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(len(all_cubes_before) - 1, len(all_cubes_after))

    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cls.cube_name)
        for dimension in cls.dimension_names:
            cls.tm1.dimensions.delete(dimension)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
