from TM1py import TM1pyQueries as TM1, TM1pyLogin, Cube, Rules
import uuid
import unittest


class TestCubeMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    cube_name = 'TM1py_unittest_cube_{}'.format(int(uuid.uuid4()))

    def test1_create_cube(self):
        all_cubes_before = self.tm1.get_all_cube_names()
        c = Cube(self.cube_name, dimensions=['plan_version','plan_business_unit'], rules=Rules(''))
        self.tm1.create_cube(c)
        all_cubes_after = self.tm1.get_all_cube_names()
        self.assertEqual(len(all_cubes_before) + 1, len(all_cubes_after))

    def test2_get_cube(self):
        c = self.tm1.get_cube(self.cube_name)
        self.assertIsInstance(c, Cube)

        cubes = self.tm1.get_all_cubes()
        control_cubes = self.tm1.get_control_cubes()
        model_cubes = self.tm1.get_model_cubes()
        self.assertEqual(len(cubes), len(control_cubes+model_cubes))


    def test3_update_cube(self):
        c = self.tm1.get_cube(self.cube_name)
        c.rules = Rules("SKIPCHECK;\nFEEDERS;")
        self.tm1.update_cube(c)
        # test if rule was actually updated
        c = self.tm1.get_cube(self.cube_name)
        self.assertTrue(c.skipcheck)

    def test4_delete_cube(self):
        all_cubes_before = self.tm1.get_all_cube_names()
        self.tm1.delete_cube(self.cube_name)
        all_cubes_after = self.tm1.get_all_cube_names()
        self.assertEqual(len(all_cubes_before) - 1, len(all_cubes_after))

    def test5_logout(self):
        self.tm1.logout()


if __name__ == '__main__':
    unittest.main()
