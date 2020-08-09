import configparser
import unittest
from pathlib import Path

from TM1py.Services import TM1Service
from TM1py.Utils import Utils


class TestUtilsMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates a dimensions and a cube to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])


    def test_get_instances_from_adminhost(self):
        servers = Utils.get_all_servers_from_adminhost(self.config['tm1srv01']['address'])
        self.assertGreater(len(servers), 0)


    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
