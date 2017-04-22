from TM1py import TM1pyLogin, TM1pyQueries as TM1, Edge, Element, Hierarchy, Dimension, ElementAttribute, Cube, Subset

import json

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # remove 'Accept' Header -> So we get @odata.count entry in response json
    tm1._client._headers.pop('Accept')

    cubes_with_cellnumber = []
    for cube in tm1.get_all_cubes():
        cube.numberCells = 1
        for dimension_name in cube.dimensions:
            response = tm1._client.GET('/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$count'.format(dimension_name, dimension_name))
            number = json.loads(response)['@odata.count']
            cube.numberCells *= number

        cubes_with_cellnumber.append(cube)

    cubes_with_cellnumber.sort(key=lambda cube: cube.numberCells, reverse=True)
    for cube in cubes_with_cellnumber:
        print('Cube: {}, Cells: {}'.format(cube.name, cube.numberCells))
