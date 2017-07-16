from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.CubeService import CubeService
from Services.DimensionService import DimensionService


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
