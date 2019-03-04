import configparser
import os
import unittest

from TM1py.Objects import User
from TM1py.Services import TM1Service
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))

PREFIX = "TM1py_Tests_"


class TestSecurityMethods(unittest.TestCase):
    tm1 = None

    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])
        cls.user_name = PREFIX + "User1"
        cls.user = User(name=cls.user_name, groups=[], password='TM1py')
        cls.group_name1 = PREFIX + "Group1"
        cls.group_name2 = PREFIX + "Group2"
        cls.user.add_group(cls.group_name1)

        if cls.user_name in CaseAndSpaceInsensitiveSet(*cls.tm1.security.get_all_user_names()):
            cls.tm1.security.delete_user(cls.user_name)

        for group in (cls.group_name1, cls.group_name2):
            if group in CaseAndSpaceInsensitiveSet(*cls.tm1.security.get_all_groups()):
                cls.tm1.security.delete_group(group)

    def setUp(self):
        self.tm1.security.create_group(self.group_name1)
        self.tm1.security.create_group(self.group_name2)
        self.tm1.security.create_user(self.user)

    def tearDown(self):
        self.tm1.security.delete_user(self.user_name)
        self.tm1.security.delete_group(self.group_name1)
        self.tm1.security.delete_group(self.group_name2)

    def test_get_user(self):
        u = self.tm1.security.get_user(self.user_name)
        # Adjust it a little bit
        u.password = 'TM1py'
        u.friendly_name = None
        self.assertEqual(u.body, self.user.body)

    def test_get_current_user(self):
        me = self.tm1.security.get_current_user()
        self.assertEqual(me.name, config['tm1srv01']['User'])

        user = self.tm1.security.get_user(config['tm1srv01']['User'])
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

    def test_get_all_users(self):
        all_users = [user.name for user in self.tm1.security.get_all_users()]
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names('}Clients', '}Clients')
        self.assertGreater(len(all_users), 0)
        self.assertIn(self.user_name, all_users)
        self.assertEqual(sorted(all_users), sorted(all_clients))

    def test_get_all_user_names(self):
        all_users = self.tm1.security.get_all_user_names()
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names('}Clients', '}Clients')
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
        clients = self.tm1.dimensions.execute_mdx("}Clients", mdx)
        self.assertGreater(len(users), 0)
        self.assertGreater(len(clients), 0)
        self.assertEqual(sorted(users), sorted(clients))

    def test_get_user_names_from_group(self):
        users = self.tm1.security.get_user_names_from_group(self.group_name1)
        mdx = "{ FILTER ( { [}Clients].Members } , [}ClientGroups].([}Groups].[" + self.group_name1 + "]) = '" + self.group_name1 + "' ) }"
        clients = self.tm1.dimensions.execute_mdx("}Clients", mdx)
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
            sorted(groups),
            sorted(self.tm1.dimensions.hierarchies.elements.get_element_names("}Groups", "}Groups"))
        )

    def test_security_refresh(self):
        response = self.tm1.security.security_refresh()
        self.assertTrue(response.ok)

    def test_create_and_delete_user(self):
        u = User(name=PREFIX + "User2", groups=())
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
        group = PREFIX + "Group3"
        groups = self.tm1.security.get_all_groups()
        if group not in CaseAndSpaceInsensitiveSet(*groups):
            self.tm1.security.create_group(group)
        groups_before_delete = self.tm1.security.get_all_groups()
        response = self.tm1.security.delete_group(group)
        self.assertTrue(response.ok)
        groups_after_delete = self.tm1.security.get_all_groups()
        self.assertIn(group, groups_before_delete)
        self.assertNotIn(group, groups_after_delete)

    @classmethod
    def teardown_class(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
