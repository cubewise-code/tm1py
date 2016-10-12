from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    cubes = tm1.get_all_cubes()
    for cube in cubes:
        if cube.has_rules and cube.rules.has_skipcheck:
            print(cube.name)





