import configparser
import unittest
from pathlib import Path

from TM1py.Services import TM1Service
from TM1py.Utils import case_and_space_insensitive_equals


class TestMonitoringService(unittest.TestCase):
    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

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

    def test_close_all_sessions(self):
        self.tm1.monitoring.close_all_sessions()

    def test_disconnect_all_users(self):
        self.tm1.monitoring.disconnect_all_users()

    def test_cancel_all_running_threads(self):
        self.tm1.monitoring.cancel_all_running_threads()

    def test_get_sessions(self):
        sessions = self.tm1.monitoring.get_sessions()
        self.assertTrue(len(sessions) > 0)
        self.assertIn('ID', sessions[0])
        self.assertIn('Context', sessions[0])
        self.assertIn('Active', sessions[0])
        self.assertIn('User', sessions[0])
        self.assertIn('Threads', sessions[0])

    def test_get_sessions_exclude_user(self):
        sessions = self.tm1.monitoring.get_sessions(include_user=False)
        self.assertTrue(len(sessions) > 0)
        self.assertIn('ID', sessions[0])
        self.assertIn('Context', sessions[0])
        self.assertIn('Active', sessions[0])
        self.assertNotIn('User', sessions[0])
        self.assertIn('Threads', sessions[0])

    def test_get_sessions_exclude_threads(self):
        sessions = self.tm1.monitoring.get_sessions(include_threads=False)
        self.assertTrue(len(sessions) > 0)
        self.assertIn('ID', sessions[0])
        self.assertIn('Context', sessions[0])
        self.assertIn('Active', sessions[0])
        self.assertIn('User', sessions[0])
        self.assertNotIn('Threads', sessions[0])

    def test_get_sessions_exclude_threads_and_user(self):
        sessions = self.tm1.monitoring.get_sessions(include_threads=False, include_user=False)
        self.assertTrue(len(sessions) > 0)
        self.assertIn('ID', sessions[0])
        self.assertIn('Context', sessions[0])
        self.assertIn('Active', sessions[0])
        self.assertNotIn('User', sessions[0])
        self.assertNotIn('Threads', sessions[0])

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
