import unittest

from TM1py.Services import TM1Service

# Configuration for tests
address = 'localhost'
port = 8001
user = 'admin'
pwd = 'apple'
ssl = False


class TestTM1pyDictMethods(unittest.TestCase):
    tm1 = TM1Service(address=address, port=port, user=user, password=pwd, ssl=ssl)

    def test_stuff(self):
        mdx_rows = '[}Clients].Members'
        mdx_columns = '[}Groups].Members'
        cube_name = '[}ClientGroups]'
        mdx = 'SELECT {} ON ROWS, {} ON COLUMNS FROM {}'.format(mdx_rows, mdx_columns, cube_name)
        data = self.tm1.data.execute_mdx(mdx)

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


