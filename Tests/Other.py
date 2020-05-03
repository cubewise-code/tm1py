import configparser
from pathlib import Path
import random
import unittest
from base64 import b64encode

from TM1py.Exceptions import TM1pyRestException, TM1pyException
from TM1py.Objects import MDXView, User
from TM1py.Services import TM1Service
from TM1py.Utils import Utils

config = configparser.ConfigParser()
config.read(Path(__file__).parent.joinpath('config.ini'))


class TestOtherMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setUpClass(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])

    @unittest.skip("Not deterministic. Needs improvement.")
    def test_mdx_from_cubeview(self):
        cube_names = self.tm1.cubes.get_all_names()
        cube_name = cube_names[random.randrange(0, len(cube_names))]
        _, public_views = self.tm1.cubes.views.get_all(cube_name=cube_name)
        # if no views on cube. Recursion
        if len(public_views) == 0:
            self.test_mdx_from_cubeview()
        else:
            # random public view on random cube
            view = public_views[random.randrange(0, len(public_views))]
            # if random view is MDXView. Recursion
            if isinstance(view, MDXView):
                self.test_mdx_from_cubeview()
            else:
                # if native view has no dimensions on the columns. Recursion
                if len(view._columns) == 0:
                    self.test_mdx_from_cubeview()
                else:
                    # sum up all numeric cells in Native View
                    data_native_view = self.tm1.cubes.cells.get_view_content(cube_name, view.name, private=False)
                    sum_native_view = sum(
                        [float(cell['Value']) for cell in data_native_view.values() if str(cell['Value']).isdigit()])

                    # get mdx from native view
                    mdx = view.as_MDX
                    # sum up all numeric cells in the response of the mdx query
                    data_mdx = self.tm1.cubes.cells.execute_mdx(mdx)
                    sum_mdx = sum([float(cell['Value']) for cell in data_mdx.values() if str(cell['Value']).isdigit()])

                    # test it !
                    self.assertEqual(sum_mdx, sum_native_view)

    def test_get_instances_from_adminhost(self):
        servers = Utils.get_all_servers_from_adminhost(config['tm1srv01']['address'])
        self.assertGreater(len(servers), 0)

    def test_tm1service_with_encrypted_password_decode_b64_as_string(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        with TM1Service(
                user=user.name,
                password=b64encode(str.encode(user._password)),
                decode_b64="True",
                base_url=self.tm1._tm1_rest._base_url,
                ssl=self.tm1._tm1_rest._ssl) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    def test_tm1service_without_encrypted_password(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        with TM1Service(
                user=user.name,
                password=user._password,
                decode_b64=False,
                base_url=self.tm1._tm1_rest._base_url,
                ssl=self.tm1._tm1_rest._ssl) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    def test_tm1service_with_encrypted_password(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        with TM1Service(
                user=user.name,
                password=b64encode(str.encode(user._password)),
                decode_b64=True,
                base_url=self.tm1._tm1_rest._base_url,
                ssl=self.tm1._tm1_rest._ssl) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    def test_tm1service_with_encrypted_password_fail(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        self.assertRaises(TM1pyRestException, TM1Service,
                          user=user.name,
                          password=b64encode(str.encode("banana")),
                          decode_b64=True,
                          base_url=self.tm1._tm1_rest._base_url,
                          ssl=self.tm1._tm1_rest._ssl)

        self.tm1.security.delete_user(user.name)

    def test_tm1service_with_plain_password(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        with TM1Service(
                user=user.name,
                password=user.password,
                base_url=self.tm1._tm1_rest._base_url,
                ssl=self.tm1._tm1_rest._ssl) as _:
            # if no exception. Login was successful
            pass
        self.tm1.security.delete_user(user.name)

    def test_tm1service_with_plain_password_fail(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)
        # test with random (wrong) password
        self.assertRaises(TM1pyRestException, TM1Service,
                          user=user.name,
                          password="banana",
                          base_url=self.tm1._tm1_rest._base_url,
                          ssl=self.tm1._tm1_rest._ssl)

        self.tm1.security.delete_user(user.name)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
