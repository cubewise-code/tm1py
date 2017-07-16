import unittest

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.DataService import DataService

# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestTM1pyDictMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)
    data_service = DataService(tm1_rest)

    def test_stuff(self):
        mdx_rows = '[}Clients].Members'
        mdx_columns = '[}Groups].Members'
        cube_name = '[}ClientGroups]'
        mdx = 'SELECT {} ON ROWS, {} ON COLUMNS FROM {}'.format(mdx_rows, mdx_columns, cube_name)
        data = self.data_service.execute_mdx(mdx)

        ### Get
        self.assertIsNotNone(data[('[}Clients].[ad min]', '[}Groups].[ADM IN]')])

        ### Delete
        self.assertTrue(('[}clients].[admin]', '[}groups].[admin]') in data)
        del data[('[}Clients].[ad min]', '[}Groups].[ADM IN]')]
        self.assertFalse(('[}clients].[admin]', '[}groups].[admin]') in data)

        ### Copy
        data_cloned = data.copy()
        self.assertTrue(data_cloned == data)
        self.assertFalse(data_cloned is data)


if __name__ == '__main__':
    unittest.main()


