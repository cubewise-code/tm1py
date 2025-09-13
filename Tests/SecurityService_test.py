import configparser
import unittest
from base64 import b64encode
from pathlib import Path

from TM1py.Exceptions import TM1pyRestException
from TM1py.Objects import User
from TM1py.Objects.User import UserType
from TM1py.Services import TM1Service
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet, verify_version
from .Utils import skip_if_version_higher_or_equal_than, skip_if_auth_not_basic


class TestSecurityService(unittest.TestCase):
    tm1: TM1Service

    prefix = "TM1py_Tests_"
    user_name = prefix + "User1"
    read_only_user_name = prefix + "Read_Only_user"
    user_name_exotic_password = "UserWithExoticPassword"
    enabled = True
    user = User(name=user_name, groups=[], password="TM1py", enabled=enabled)
    read_only_user = User(name=read_only_user_name, groups=[], password="TM1py", enabled=True)
    group_name1 = prefix + "Group1"
    group_name2 = prefix + "Group2"
    user.add_group(group_name1)

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        if cls.user_name in CaseAndSpaceInsensitiveSet(*cls.tm1.security.get_all_user_names()):
            cls.tm1.security.delete_user(cls.user_name)

        for group in (cls.group_name1, cls.group_name2):
            if group in CaseAndSpaceInsensitiveSet(*cls.tm1.security.get_all_groups()):
                cls.tm1.security.delete_group(group)

    def setUp(self):
        if not self.tm1.security.group_exists(self.group_name1):
            self.tm1.security.create_group(self.group_name1)
        if not self.tm1.security.group_exists(self.group_name2):
            self.tm1.security.create_group(self.group_name2)
        if not self.tm1.security.user_exists(self.user.name):
            self.tm1.security.create_user(self.user)
        if not self.tm1.security.user_exists(self.read_only_user.name):
            self.tm1.security.create_user(self.read_only_user)
        if not verify_version(required_version="12", version=self.tm1.version):
            self.tm1.cells.write_values(
                cube_name="}ClientProperties", cellset_as_dict={(self.read_only_user_name, "ReadOnlyUser"): 1}
            )

    def tearDown(self):
        self.tm1.security.delete_user(self.user_name)
        self.tm1.security.delete_user(self.read_only_user_name)
        self.tm1.security.delete_group(self.group_name1)
        self.tm1.security.delete_group(self.group_name2)
        if self.user_name_exotic_password in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(self.user_name_exotic_password)

    def test_get_user(self):
        u = self.tm1.security.get_user(self.user_name)
        # Adjust it a little bit
        u.password = "TM1py"
        u.friendly_name = None
        self.assertEqual(u.body, self.user.body)

    def test_get_current_user(self):
        me = self.tm1.security.get_current_user()
        self.assertIsNotNone(me.enabled)
        self.assertIsNotNone(me.friendly_name)
        self.assertIsNotNone(me.groups)
        self.assertIsNotNone(me.name)

        user = self.tm1.security.get_user(me.name)
        self.assertEqual(me, user)

    def test_update_user(self):
        # get user
        u = self.tm1.security.get_user(self.user_name)
        # update user. Add Group
        u.add_group(self.group_name2)
        self.tm1.security.update_user(u)
        # test it !
        groups = self.tm1.security.get_groups(u.name)
        self.assertIn(self.group_name2, groups)
        # update user. Remove Group
        u.remove_group(self.group_name2)
        self.tm1.security.update_user(u)
        # test it !
        groups = self.tm1.security.get_groups(u.name)
        self.assertNotIn(self.group_name2, groups)

    def test_user_type_invalid_type(self):
        with self.assertRaises(ValueError) as _:
            self.tm1.security.create_user(User("not_relevant", groups=["ADMIN"], user_type=3))

    def test_user_type_invalid_str(self):
        with self.assertRaises(ValueError) as e:
            self.tm1.security.create_user(User("not_relevant", groups=["ADMIN"], user_type="not_a_valid_type"))

    def test_user_type_derive_user_from_groups(self):
        user = User("not_relevant", groups=["Marketing"], user_type=None)
        self.assertEqual(user.user_type, UserType.User)

    def test_user_type_derive_security_admin_from_groups(self):
        user = User("not_relevant", groups=["SecurityAdmin"], user_type=None)
        self.assertEqual(user.user_type, UserType.SecurityAdmin)

    def test_user_type_derive_data_admin_from_groups(self):
        user = User("not_relevant", groups=["DataAdmin"], user_type=None)
        self.assertEqual(user.user_type, UserType.DataAdmin)

    def test_user_type_derive_admin_from_groups(self):
        user = User("not_relevant", groups=["ADMIN"], user_type=None)
        self.assertEqual(user.user_type, UserType.Admin)

    def test_user_type_derive_operations_admin_from_groups(self):
        user = User("not_relevant", groups=["OperationsAdmin"], user_type=None)
        self.assertEqual(user.user_type, UserType.OperationsAdmin)

    @skip_if_version_higher_or_equal_than(version="12")
    def test_update_user_properties(self):
        # get user
        u = self.tm1.security.get_user(self.user_name)
        self.assertNotIn("DataAdmin", u.groups)

        # update enabled
        u.enabled = False
        # update UserType
        u.user_type = UserType.DataAdmin
        # update user. Add Group
        u.add_group(self.group_name2)
        self.assertIn("DataAdmin", u.groups)

        self.tm1.security.update_user(u)
        u = self.tm1.security.get_user(u.name)

        self.assertFalse(u.enabled)
        self.assertEqual(u.user_type, UserType.DataAdmin)
        self.assertIn("DataAdmin", u.groups)

    @skip_if_version_higher_or_equal_than(version="12")
    def test_update_user_properties_with_type_as_str(self):
        # get user
        u = self.tm1.security.get_user(self.user_name)
        self.assertEqual(u.user_type, UserType.User)
        self.assertNotIn("DataAdmin", u.groups)

        # update enabled
        u.enabled = False
        # update UserType
        u.user_type = "dataadmin"
        # update user. Add Group
        u.add_group(self.group_name2)

        self.tm1.security.update_user(u)

        u = self.tm1.security.get_user(u.name)

        self.assertFalse(u.enabled)
        self.assertEqual(u.user_type, UserType.DataAdmin)
        self.assertIn("DataAdmin", u.groups)

    def test_get_all_users(self):
        all_users = [user.name for user in self.tm1.security.get_all_users()]
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names("}Clients", "}Clients")
        self.assertGreater(len(all_users), 0)
        self.assertIn(self.user_name, all_users)
        self.assertEqual(sorted(all_users), sorted(all_clients))

    def test_get_all_user_names(self):
        all_users = self.tm1.security.get_all_user_names()
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names("}Clients", "}Clients")
        self.assertGreater(len(all_users), 0)
        self.assertIn(self.user_name, all_users)
        self.assertEqual(sorted(all_users), sorted(all_clients))

    def test_add_user_to_groups(self):
        self.tm1.security.add_user_to_groups(self.user_name, (self.group_name2,))
        user = self.tm1.security.get_user(self.user_name)
        self.assertIn(self.group_name2, user.groups)

    def test_remove_user_from_group(self):
        self.tm1.security.remove_user_from_group(self.group_name1, self.user_name)
        user = self.tm1.security.get_user(self.user_name)
        self.assertNotIn(self.group_name1, user.groups)

    def test_get_users_from_group(self):
        users = [user.name for user in self.tm1.security.get_users_from_group("AdMiN")]
        mdx = "{ FILTER ( { [}Clients].Members } , [}ClientGroups].([}Groups].[ADMIN]) = 'ADMIN' ) }"
        clients = self.tm1.elements.execute_set_mdx_element_names(mdx)
        self.assertGreater(len(users), 0)
        self.assertGreater(len(clients), 0)
        self.assertEqual(sorted(users), sorted(clients))

    def test_get_user_names_from_group(self):
        users = self.tm1.security.get_user_names_from_group(self.group_name1)
        mdx = (
            "{ FILTER ( { [}Clients].Members } , [}ClientGroups].([}Groups].["
            + self.group_name1
            + "]) = '"
            + self.group_name1.replace("'", "''")
            + "' ) }"
        )
        clients = self.tm1.elements.execute_set_mdx_element_names(mdx)
        self.assertGreater(len(users), 0)
        self.assertGreater(len(clients), 0)
        self.assertEqual(sorted(users), sorted(clients))

    def test_get_groups_from_user(self):
        groups = self.tm1.security.get_groups(self.user_name)
        self.assertIn(self.group_name1, groups)

        groups = self.tm1.security.get_groups(" ".join(self.user_name.upper()))
        self.assertIn(self.group_name1, groups)

    def test_get_groups(self):
        groups = self.tm1.security.get_all_groups()
        self.assertGreater(len(groups), 0)
        self.assertEqual(
            sorted(groups), sorted(self.tm1.dimensions.hierarchies.elements.get_element_names("}Groups", "}Groups"))
        )

    def test_security_refresh(self):
        response = self.tm1.security.security_refresh()
        self.assertTrue(response.ok)

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
    def test_auth_with_exotic_characters_in_password(self):
        exotic_password = "d'8!?:Y4"

        # create user
        user = User(name=self.user_name_exotic_password, groups=("ADMIN",), password=exotic_password)
        self.tm1.security.create_user(user)

        # login as user with exotic password
        kwargs = dict(self.config["tm1srv01"])
        kwargs["user"] = user.name
        kwargs["password"] = exotic_password
        # raises TM1pyException if login fails
        with TM1Service(**kwargs) as tm1_second_conn:
            self.assertEqual(tm1_second_conn.whoami.name, user.name)

    def test_create_and_delete_user(self):
        u = User(name=self.prefix + "User2", groups=())
        all_users = self.tm1.security.get_all_user_names()
        if u.name not in CaseAndSpaceInsensitiveSet(*all_users):
            self.tm1.security.create_user(u)
        users_before_delete = self.tm1.security.get_all_user_names()
        response = self.tm1.security.delete_user(u.name)
        self.assertTrue(response.ok)
        users_after_delete = self.tm1.security.get_all_user_names()
        self.assertIn(u.name, CaseAndSpaceInsensitiveSet(*users_before_delete))
        self.assertNotIn(u.name, CaseAndSpaceInsensitiveSet(*users_after_delete))

    def test_create_and_delete_group(self):
        group = self.prefix + "Group3"
        groups = self.tm1.security.get_all_groups()
        if group not in CaseAndSpaceInsensitiveSet(*groups):
            self.tm1.security.create_group(group)
        groups_before_delete = self.tm1.security.get_all_groups()
        response = self.tm1.security.delete_group(group)
        self.assertTrue(response.ok)
        groups_after_delete = self.tm1.security.get_all_groups()
        self.assertIn(group, groups_before_delete)
        self.assertNotIn(group, groups_after_delete)

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
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
            ssl=self.tm1._tm1_rest._ssl,
        ) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
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
            ssl=self.tm1._tm1_rest._ssl,
        ) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
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
            ssl=self.tm1._tm1_rest._ssl,
        ) as _:
            # if no exception. Login was successful
            pass

        self.tm1.security.delete_user(user.name)

    @skip_if_version_higher_or_equal_than(version="12")
    def test_tm1service_with_encrypted_password_fail(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        self.assertRaises(
            TM1pyRestException,
            TM1Service,
            user=user.name,
            password=b64encode(str.encode("banana")),
            decode_b64=True,
            base_url=self.tm1._tm1_rest._base_url,
            ssl=self.tm1._tm1_rest._ssl,
        )

        self.tm1.security.delete_user(user.name)

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
    def test_tm1service_with_plain_password(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)

        with TM1Service(
            user=user.name, password=user.password, base_url=self.tm1._tm1_rest._base_url, ssl=self.tm1._tm1_rest._ssl
        ) as _:
            # if no exception. Login was successful
            pass
        self.tm1.security.delete_user(user.name)

    @skip_if_version_higher_or_equal_than(version="12")
    def test_tm1service_with_plain_password_fail(self):
        user_name = "TM1py user name"
        user = User(name=user_name, groups=["ADMIN"], password="apple")
        if user.name in self.tm1.security.get_all_user_names():
            self.tm1.security.delete_user(user_name)
        self.tm1.security.create_user(user)
        # test with random (wrong) password
        self.assertRaises(
            TM1pyRestException,
            TM1Service,
            user=user.name,
            password="banana",
            base_url=self.tm1._tm1_rest._base_url,
            ssl=self.tm1._tm1_rest._ssl,
        )

        self.tm1.security.delete_user(user.name)

    def test_user_exists_true(self):
        self.assertTrue(self.tm1.security.user_exists(user_name=self.user_name))

    def test_user_exists_false(self):
        self.assertFalse(self.tm1.security.user_exists(user_name="NotAValidName"))

    def test_group_exists_true(self):
        self.assertTrue(self.tm1.security.group_exists(group_name=self.group_name1))

    def test_group_exists_false(self):
        self.assertFalse(self.tm1.security.group_exists(group_name="NotAValidName"))

    @skip_if_version_higher_or_equal_than(version="12")
    def test_impersonate(self):
        tm1 = TM1Service(**self.config["tm1srv01"])
        self.assertNotEqual(self.user_name, tm1.whoami.name)

        tm1 = TM1Service(**self.config["tm1srv01"], impersonate=self.user_name)
        self.assertEqual(self.user_name, tm1.whoami.name)

    def test_get_custom_security_groups(self):
        custom_groups = self.tm1.security.get_custom_security_groups()

        self.assertNotIn("Admin", CaseAndSpaceInsensitiveSet(*custom_groups))
        self.assertNotIn("DataAdmin", CaseAndSpaceInsensitiveSet(*custom_groups))
        self.assertNotIn("SecurityAdmin", CaseAndSpaceInsensitiveSet(*custom_groups))
        self.assertNotIn("OperationsAdmin", CaseAndSpaceInsensitiveSet(*custom_groups))
        self.assertNotIn("}tp_Everyone", CaseAndSpaceInsensitiveSet(*custom_groups))

        self.assertIn(self.group_name1, CaseAndSpaceInsensitiveSet(*custom_groups))
        self.assertIn(self.group_name2, CaseAndSpaceInsensitiveSet(*custom_groups))

        self.assertNotIn("NotExistingGroup", CaseAndSpaceInsensitiveSet(*custom_groups))

    @skip_if_version_higher_or_equal_than(version="12")
    def test_get_read_only_users(self):
        read_only_users = self.tm1.security.get_read_only_users()

        self.assertEqual(1, len(read_only_users))
        self.assertEqual(self.read_only_user_name, read_only_users[0])

    @skip_if_auth_not_basic
    @skip_if_version_higher_or_equal_than(version="12")
    def test_update_user_password(self):
        self.tm1.security.update_user_password(user_name=self.user.name, password="new_password123")

        with TM1Service(
            user=self.user.name,
            password="new_password123",
            base_url=self.tm1._tm1_rest._base_url,
            ssl=self.tm1._tm1_rest._ssl,
        ) as _:
            # if no exception. Login was successful
            pass

    @classmethod
    def teardown_class(cls):
        cls.tm1.logout()


if __name__ == "__main__":
    unittest.main()
