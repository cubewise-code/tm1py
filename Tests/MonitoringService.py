import configparser
import unittest
from pathlib import Path

from TM1py.Services import TM1Service
from TM1py.Utils import case_and_space_insensitive_equals

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))

PREFIX = "TM1py_Tests_MonitoringService_"


class TestMonitoringMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    def test_get_threads(self):
        threads = self.tm1.monitoring.get_threads()
        self.assertTrue(any(thread["Function"] == "GET /api/v1/Threads" for thread in threads))

    def test_get_active_users(self):
        current_user = self.tm1.security.get_current_user()
        active_users = self.tm1.monitoring.get_active_users()
        self.assertTrue(any(case_and_space_insensitive_equals(user.name, current_user.name) for user in active_users))

    def test_user_is_active(self):
        current_user = self.tm1.security.get_current_user()
        self.assertTrue(self.tm1.monitoring.user_is_active(current_user.name))

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
