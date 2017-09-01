import unittest
import uuid

from TM1py.Objects import User
from TM1py.Services import TM1Service


from .config import test_config


class TestUserMethods(unittest.TestCase):
    tm1 = TM1Service(**test_config)

    user_name = str(uuid.uuid4())
    group_name = str(uuid.uuid4())
    user = User(name=user_name, groups=[], password='TM1py')

    # Create Group for unittests
    @classmethod
    def setup_class(cls):
        code = "AddGroup('{}');".format(cls.group_name)
        cls.tm1.processes.execute_ti_code([code])

    def test1_create_user(self):
        all_users_before = self.tm1.security.get_all_users()
        self.tm1.security.create_user(self.user)
        all_users_after = self.tm1.security.get_all_users()
        # test it!
        self.assertEqual(len(all_users_before) + 1, len(all_users_after))

    def test2_get_user(self):
        u = self.tm1.security.get_user(self.user_name)
        # Adjust it a little bit
        u.password = 'TM1py'
        u.friendly_name = None

        # test it !
        self.assertEqual(u.body, self.user.body)

    def test3_update_user(self):
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

    def test4_delete_user(self):
        users_before = self.tm1.security.get_all_users()
        self.tm1.security.delete_user(self.user_name)
        users_after = self.tm1.security.get_all_users()

        # test it !
        self.assertEqual(len(users_before) - 1, len(users_after))

    @classmethod
    def teardown_class(cls):
        # Delete Group
        code = "DeleteGroup('{}');".format(cls.group_name)
        cls.tm1.processes.execute_ti_code([code])
        cls.tm1.logout()

if __name__ == '__main__':
    unittest.main()
