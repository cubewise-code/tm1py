from TM1py import TM1pyQueries as TM1, TM1pyLogin, User

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    u = User(name='Manny', friendly_name='MP', user_type='ADMIN', groups=[], password='apple')
    tm1.create_user(u)
