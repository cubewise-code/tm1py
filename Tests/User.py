import uuid
import unittest

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.UserService import UserService
from Services.ProcessService import ProcessService

from Objects.User import User

# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'


class TestUserMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)
    process_service = ProcessService(tm1_rest)
    user_service = UserService(tm1_rest)
    user_name = str(uuid.uuid4())
    group_name = str(uuid.uuid4())
    user = User(name=user_name, groups=[], password='TM1py')

    # Create Group for unittests
    @classmethod
    def setup_class(cls):
        code = "AddGroup('{}');".format(cls.group_name)
        cls.process_service.execute_ti_code([code])

    def test1_create_user(self):
        all_users_before = self.user_service.get_all()
        self.user_service.create(self.user)
        all_users_after = self.user_service.get_all()
        # test it!
        self.assertEqual(len(all_users_before) + 1, len(all_users_after))

    def test2_get_user(self):
        u = self.user_service.get(self.user_name)
        # Adjust it a little bit
        u.password = 'TM1py'
        u.friendly_name = None

        # test it !
        self.assertEqual(u.body, self.user.body)

    def test3_update_user(self):
        # get user
        u = self.user_service.get(self.user_name)
        # update user. Add Group
        u.add_group(self.group_name)
        self.user_service.update(u)
        # test it !
        groups = self.user_service.get_groups(u.name)
        self.assertIn(self.group_name, groups)
        # update user. Remove Group
        u.remove_group(self.group_name)
        self.user_service.update(u)
        # test it !
        groups = self.user_service.get_groups(u.name)
        self.assertNotIn(self.group_name, groups)

    def test4_delete_user(self):
        users_before = self.user_service.get_all()
        self.user_service.delete(self.user_name)
        users_after = self.user_service.get_all()

        # test it !
        self.assertEqual(len(users_before) - 1, len(users_after))

    @classmethod
    def teardown_class(cls):
        # Delete Group
        code = "DeleteGroup('{}');".format(cls.group_name)
        cls.process_service.execute_ti_code([code])
        cls.tm1_rest.logout()

if __name__ == '__main__':
    unittest.main()
