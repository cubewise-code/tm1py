from TM1py.Services import CubeService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    cubes = cube_service.get_all()

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

    cube = cube_service.get('plan_Report')
    # print plain rule stmts
    print("Rule Statements:")
    for stmt in cube.rules.rule_statements:
        print(stmt)
    # print plain feeder stmts
    print("Feeder Statements:")
    for stmt in cube.rules.feeder_statements:
        print(stmt)
