from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    cubes = tm1.get_all_cubes()

    print("Cubes with SKIPCHECK:")
    for cube in cubes:
        if cube.skipcheck:
            print(cube.name)

    print("Cubes with UNDEFVALS:")
    for cube in cubes:
        if cube.undefvals:
            print(cube.name)

    print("Cubes with Rules:")
    cubes_with_rules = (c for c in cubes if c.has_rules)
    for c in cubes_with_rules:
        print("{} has {} rule statements and {} feeder statements."
              .format(c.name, str(len(c.rules.rule_statements)), str(len(c.rules.feeder_statements))))





