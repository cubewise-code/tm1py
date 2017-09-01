import unittest

from TM1py.Services import TM1Service

from .config import test_config


class TestTM1pyDictMethods(unittest.TestCase):
    tm1 = TM1Service(**test_config)

    def test_stuff(self):
        mdx_rows = '[}Clients].Members'
        mdx_columns = '[}Groups].Members'
        cube_name = '[}ClientGroups]'
        mdx = 'SELECT {} ON ROWS, {} ON COLUMNS FROM {}'.format(mdx_rows, mdx_columns, cube_name)
        data = self.tm1.cubes.cells.execute_mdx(mdx)

        # Get
        self.assertIsNotNone(data[('[}Clients].[ad min]', '[}Groups].[ADM IN]')])

        # Delete
        self.assertTrue(('[}clients].[admin]', '[}groups].[admin]') in data)
        del data[('[}Clients].[ad min]', '[}Groups].[ADM IN]')]
        self.assertFalse(('[}clients].[admin]', '[}groups].[admin]') in data)

        # Copy
        data_cloned = data.copy()
        self.assertTrue(data_cloned == data)
        self.assertFalse(data_cloned is data)


if __name__ == '__main__':
    unittest.main()


