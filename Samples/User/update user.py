from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    u = tm1.get_user('Great Panda')
    u.friendly_name = 'Pandabear'
    u.password = 'Bamboo'
    u.add_group('Mammals')
    u.add_group('10000')
    tm1.update_user(u)
