from TM1py import TM1pyQueries as TM1, TM1pyLogin, User

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    u = User(name='Hodor Hodor', friendly_name='Hodor', groups=['Admin'], password='apple')
    tm1.create_user(u)
