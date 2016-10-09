from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    for user in tm1.get_users_from_group('ADMIN'):
        pass
    for user in tm1.get_active_users():
        pass
    for group in tm1.get_all_groups():
        pass




