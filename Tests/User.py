from TM1py import TM1pyQueries as TM1, TM1pyLogin, User
import uuid
import unittest


class TestUserMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

