import json

from TM1py.Services import CubeService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)

    cubes_with_cellnumber = []
    for cube in cube_service.get_all():
        cube.numberCells = 1
        for dimension_name in cube.dimensions:
            response = tm1_rest.GET('/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements/$count'
                                    .format(dimension_name, dimension_name))
            number = json.loads(response)
            cube.numberCells *= number
        cubes_with_cellnumber.append(cube)

    cubes_with_cellnumber.sort(key=lambda c: c.numberCells, reverse=True)
    for cube in cubes_with_cellnumber:
        print('Cube: {}, Cells: {}'.format(cube.name, cube.numberCells))
