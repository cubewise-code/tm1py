import configparser
import unittest
from pathlib import Path

from TM1py.Services import TM1Service
from TM1py.Utils import case_and_space_insensitive_equals

PREFIX = "TM1py_Tests_MonitoringService_"


class TestMonitoringMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        config = configparser.ConfigParser()
        config.read(Path(__file__).parent.joinpath('config.ini'))
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

    def test_get_sessions(self):
        current_user = self.tm1.security.get_current_user()
        sessions = self.tm1.monitoring.get_sessions()
        self.assertTrue(any(case_and_space_insensitive_equals(session["User"]["Name"], current_user.name)
                            for session
                            in sessions if session["User"]))

    def test_close_all_sessions(self):
        self.tm1.monitoring.close_all_sessions()

    def test_disconnect_all_users(self):
        self.tm1.monitoring.disconnect_all_users()

    def test_cancel_all_running_threads(self):
        self.tm1.monitoring.cancel_all_running_threads()

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
