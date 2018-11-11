import configparser
import os
import unittest
import uuid
from random import shuffle

from TM1py.Objects import Cube
from TM1py.Objects import Rules
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestCubeMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])
        cls.cube_name = 'TM1py_unittest_cube_{}'.format(str(uuid.uuid4()))

        dimensions = cls.tm1.dimensions.get_all_names()
        shuffle(dimensions)
        dimensions = dimensions[0:10]

        c = Cube(cls.cube_name, dimensions=dimensions, rules=Rules(''))
        cls.tm1.cubes.create(c)

    def test_get_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        self.assertIsInstance(c, Cube)

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
        self.assertTrue(c.skipcheck)

    def test_exists(self):
        self.assertTrue(self.tm1.cubes.exists(self.cube_name))
        self.assertFalse(self.tm1.cubes.exists(uuid.uuid4()))

    def test_create_delete_cube(self):
        cube_name = str(uuid.uuid4())
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
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
