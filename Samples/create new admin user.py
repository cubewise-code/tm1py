from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get existing ADMIN
    u = tm1.get_user('admin')

    # edit it
    u.name = 'Han Solo'
    u.friendly_name = 'Han'
    u.password = 'MilleniumFalcon'
    u.add_group('Resistance')

    # create new user on TM1 Server
    tm1.create_user(u)
