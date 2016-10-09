from TM1py import TM1pyQueries as TM1, TM1pyLogin, Cube
import uuid
import unittest


class TestCubeMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    def test1_create_user(self):
        pass

    def test2_get_user(self):
        pass

    def test3_update_user(self):
        pass

    def test4_delete_user(self):
        pass

    def test5_logout(self):
        pass


if __name__ == '__main__':
    unittest.main()
