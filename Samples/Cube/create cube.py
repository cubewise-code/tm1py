from TM1py import TM1pyQueries as TM1, TM1pyLogin, Cube

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    cube = Cube(name='Rubiks Cube', dimensions=['red', 'green', 'blue', 'yellow'], rules='')
    tm1.create_cube(cube)
