import unittest
import uuid
from random import shuffle

from TM1py.Objects import Cube
from TM1py.Objects import Rules

from TM1py.Services import TM1Service


# Configuration for tests
address = 'localhost'
port = 8001
user = 'admin'
pwd = 'apple'
ssl = False


class TestCubeMethods(unittest.TestCase):
    tm1 = TM1Service(address=address, port=port, user=user, password=pwd, ssl=ssl)

    cube_name = 'TM1py_unittest_cube_{}'.format(str(uuid.uuid4()))

    def test1_create_cube(self):
        all_cubes_before = self.tm1.cubes.get_all_names()

        dimensions = self.tm1.dimensions.get_all_names()
        shuffle(dimensions)

        c = Cube(self.cube_name, dimensions=dimensions[0:10], rules=Rules(''))
        self.tm1.cubes.create(c)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(len(all_cubes_before) + 1, len(all_cubes_after))

    def test2_get_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        self.assertIsInstance(c, Cube)

        cubes = self.tm1.cubes.get_all()
        control_cubes = self.tm1.cubes.get_control_cubes()
        model_cubes = self.tm1.cubes.get_model_cubes()
        self.assertEqual(len(cubes), len(control_cubes+model_cubes))

    def test3_update_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        c.rules = Rules("SKIPCHECK;\nFEEDERS;")
        self.tm1.cubes.update(c)
        # test if rule was actually updated
        c = self.tm1.cubes.get(self.cube_name)
        self.assertTrue(c.skipcheck)

    def test4_delete_cube(self):
        all_cubes_before = self.tm1.cubes.get_all_names()
        self.tm1.cubes.delete(self.cube_name)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(len(all_cubes_before) - 1, len(all_cubes_after))

    def test5_logout(self):
        self.tm1.logout()


if __name__ == '__main__':
    unittest.main()
