from TM1py.Services import CubeService
from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # Setup Services
    cube_service = CubeService(tm1_rest)
    dimension_service = DimensionService(tm1_rest)
    # get all dimensions
    all_dimensions = dimension_service.get_all_names()
    # get all cubes
    all_cubes = cube_service.get_all()
    # find used dimensions
    used_dimensions = set()
    for cube in all_cubes:
        used_dimensions.update(cube.dimensions)
    # determine unused dimensions
    unused_dimensions = set(all_dimensions) - used_dimensions

    print(unused_dimensions)
