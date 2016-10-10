from TM1py import TM1pyQueries as TM1, TM1pyLogin, User
import uuid
import unittest


class TestUserMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)

    user_name = str(uuid.uuid4())

    def test1_create_user(self):
        all_users_before = self.tm1.get_all_users()
        u = User(name=self.user_name, groups=[], password='TM1py')
        self.tm1.create_user(u)
        all_users_after = self.tm1.get_all_users()
        self.assertEqual(all_users_before + 1, all_users_after)

    def test2_get_user(self):
        u = self.tm1.get_user(self.user_name)
        self.assertIsInstance(u, User)

    def test3_update_user(self):
        # get user
        u = self.tm1.get_user(self.user_name)
        # update user. Add Group
        u.add_group('10110')
        self.tm1.update_user(u)
        # test
        groups = self.tm1.get_groups_from_user(u.name)
        self.assertIn('10110',groups)
        # update user. Remove Group
        u.remove_group('10110')
        self.tm1.update_user(u)
        # test
        groups = self.tm1.get_groups_from_user(u.name)
        self.assertNotIn('10110', groups)


    def test4_delete_user(self):
        users_before = self.tm1.get_all_users()
        self.tm1.delete_user(self.user_name)
        users_after = self.tm1.get_all_users()
        self.assertEqual(len(users_before) - 1, len(users_after))


    def test5_logout(self):
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
