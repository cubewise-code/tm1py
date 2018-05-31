import unittest
import configparser
import os

from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestTM1pyDictMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    def test_all(self):
        mdx_rows = '[}Clients].Members'
        mdx_columns = '[}Groups].Members'
        cube_name = '[}ClientGroups]'
        mdx = 'SELECT {} ON ROWS, {} ON COLUMNS FROM {}'.format(mdx_rows, mdx_columns, cube_name)
        data = self.tm1.cubes.cells.execute_mdx(mdx)

        # Get
        if self.tm1.version[0:2] == '10':
            coordinates = ('[}Clients].[ad min]', '[}Groups].[ADM IN]')
        else:
            coordinates = ('[}Clients].[}Clients].[ad min]', '[}Groups].[}Groups].[ADM IN]')
        self.assertIsNotNone(data[coordinates])

        # Delete
        if self.tm1.version[0:2] == '10':
            coordinates = ('[}clients].[}clients].[admin]', '[}groups].[}groups].[admin]')
        else:
            coordinates = ('[}clients].[}clients].[admin]', '[}groups].[}groups].[admin]')
        self.assertTrue(coordinates in data)
        del data[coordinates]
        self.assertFalse(coordinates in data)

        # Copy
        data_cloned = data.copy()
        self.assertTrue(data_cloned == data)
        self.assertFalse(data_cloned is data)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()


