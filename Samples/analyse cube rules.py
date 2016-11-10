from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    cubes = tm1.get_all_cubes()

    # cubes with SKIPCHECK
    cubes_with_skipcheck = [cube.name for cube in cubes if cube.skipcheck]
    print("Cubes with SKIPCHECK:")
    print(cubes_with_skipcheck)

    # cubes with UNDEFVALS
    cubes_with_undefvals = [cube.name for cube in cubes if cube.undefvals]
    print("Cubes with UNDEFVALS:")
    print(cubes_with_undefvals)

    # cubes ordered by the number of rule statements
    cubes.sort(key=lambda cube: len(cube.rules.rule_statements) if cube.has_rules else 0, reverse=True)
    print("Cubes sorted by number of Rule Statements:")
    print([cube.name for cube in cubes])

    # cubes ordered by the number of feeder statements
    cubes.sort(key=lambda cube: len(cube.rules.feeder_statements) if cube.has_rules else 0, reverse=True)
    print("Cubes sorted by number of Feeder Statements:")
    print([cube.name for cube in cubes])








