import unittest
import uuid
import os
import configparser

from TM1py.Objects import User
from TM1py.Services import TM1Service

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))


class TestSecurityMethods(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.tm1 = TM1Service(**config['tm1srv01'])
        cls.user_name = str(uuid.uuid4())
        cls.user = User(name=cls.user_name, groups=[], password='TM1py')

        # Create Group for unittests
        cls.group_name = str(uuid.uuid4())
        code = "AddGroup('{}');".format(cls.group_name)
        cls.tm1.processes.execute_ti_code([code])

    def test01_create_user(self):
        all_users_before = self.tm1.security.get_all_users()
        self.tm1.security.create_user(self.user)
        all_users_after = self.tm1.security.get_all_users()
        # test it!
        self.assertEqual(len(all_users_before) + 1, len(all_users_after))

    def test02_get_user(self):
        u = self.tm1.security.get_user(self.user_name)
        # Adjust it a little bit
        u.password = 'TM1py'
        u.friendly_name = None
        self.assertEqual(u.body, self.user.body)

    def test03_update_user(self):
        # get user
        u = self.tm1.security.get_user(self.user_name)
        # update user. Add Group
        u.add_group(self.group_name)
        self.tm1.security.update_user(u)
        # test it !
        groups = self.tm1.security.get_groups(u.name)
        self.assertIn(self.group_name, groups)
        # update user. Remove Group
        u.remove_group(self.group_name)
        self.tm1.security.update_user(u)
        # test it !
        groups = self.tm1.security.get_groups(u.name)
        self.assertNotIn(self.group_name, groups)

    def test05_get_all_users(self):
        all_users = [user.name for user in self.tm1.security.get_all_users()]
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names('}Clients', '}Clients')
        self.assertGreater(len(all_users), 0)
        self.assertIn(self.user_name, all_users)
        self.assertEqual(sorted(all_users), sorted(all_clients))

    def test06_get_all_user_names(self):
        all_users = self.tm1.security.get_all_user_names()
        all_clients = self.tm1.dimensions.hierarchies.elements.get_element_names('}Clients', '}Clients')
        self.assertGreater(len(all_users), 0)
        self.assertIn(self.user_name, all_users)
        self.assertEqual(sorted(all_users), sorted(all_clients))

    def test07_add_user_to_groups(self):
        self.tm1.security.add_user_to_groups(self.user_name, (self.group_name,))
        user = self.tm1.security.get_user(self.user_name)
        self.assertIn(self.group_name.upper(), user.groups)

    def test08_remove_user_from_group(self):
        self.tm1.security.remove_user_from_group(self.group_name, self.user_name)
        user = self.tm1.security.get_user(self.user_name)
        self.assertNotIn(self.group_name.upper(), user.groups)

    def test09_get_all_users_from_group(self):
        users = [user.name for user in self.tm1.security.get_users_from_group("AdMiN")]
        mdx = "{ FILTER ( { [}Clients].Members } , [}ClientGroups].([}Groups].[ADMIN]) = 'ADMIN' ) }"
        clients = self.tm1.dimensions.execute_mdx("}Clients", mdx)
        self.assertGreater(len(users), 0)
        self.assertGreater(len(clients), 0)
        self.assertEqual(sorted(users), sorted(clients))

    def test10_get_groups_from_user(self):
        groups = self.tm1.security.get_groups("AdMiN ")
        self.assertIn("ADMIN", groups)

    def test11_get_all_groups(self):
        groups = self.tm1.security.get_all_groups()
        self.assertGreater(len(groups), 0)
        self.assertEqual(sorted(groups),
                         sorted(self.tm1.dimensions.hierarchies.elements.get_element_names("}Groups", "}Groups")))

    def test12_security_refresh(self):
        self.tm1.security.security_refresh()

    def test13_delete_user(self):
        users_before = self.tm1.security.get_all_users()
        self.tm1.security.delete_user(self.user_name)
        users_after = self.tm1.security.get_all_users()
        self.assertEqual(len(users_before) - 1, len(users_after))

    @classmethod
    def teardown_class(cls):
        # Delete Group
        code = "DeleteGroup('{}');".format(cls.group_name)
        cls.tm1.processes.execute_ti_code([code])
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()
