from TM1py import TM1pyQueries as TM1, TM1pyLogin, Cube, Rules

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    c = tm1.get_cube('Rubiks Cube')
    r = Rules("SKIPCHECK;\n['red':'e1'] = N: 1;")
    c.rules = r
    tm1.update_cube(c)

