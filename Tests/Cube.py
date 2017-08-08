import unittest
import uuid
from random import shuffle

from TM1py.Objects import Cube
from TM1py.Objects import Rules

from TM1py.Services import CubeService
from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestCubeMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)
    cube_service = CubeService(tm1_rest)
    dimension_service = DimensionService(tm1_rest)

    cube_name = 'TM1py_unittest_cube_{}'.format(str(uuid.uuid4()))

    def test1_create_cube(self):
        all_cubes_before = self.cube_service.get_all_names()

        dimensions = self.dimension_service.get_all_names()
        shuffle(dimensions)

        c = Cube(self.cube_name, dimensions=dimensions[0:10], rules=Rules(''))
        self.cube_service.create(c)
        all_cubes_after = self.cube_service.get_all_names()
        self.assertEqual(len(all_cubes_before) + 1, len(all_cubes_after))

    def test2_get_cube(self):
        c = self.cube_service.get(self.cube_name)
        self.assertIsInstance(c, Cube)

        cubes = self.cube_service.get_all()
        control_cubes = self.cube_service.get_control_cubes()
        model_cubes = self.cube_service.get_model_cubes()
        self.assertEqual(len(cubes), len(control_cubes+model_cubes))

    def test3_update_cube(self):
        c = self.cube_service.get(self.cube_name)
        c.rules = Rules("SKIPCHECK;\nFEEDERS;")
        self.cube_service.update(c)
        # test if rule was actually updated
        c = self.cube_service.get(self.cube_name)
        self.assertTrue(c.skipcheck)

    def test4_delete_cube(self):
        all_cubes_before = self.cube_service.get_all_names()
        self.cube_service.delete(self.cube_name)
        all_cubes_after = self.cube_service.get_all_names()
        self.assertEqual(len(all_cubes_before) - 1, len(all_cubes_after))

    def test5_logout(self):
        self.tm1_rest.logout()


if __name__ == '__main__':
    unittest.main()
