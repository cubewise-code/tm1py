import re

from TM1py.Services import CubeService
from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import SubsetService
from TM1py.Services import ViewService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    dimension_service = DimensionService(tm1_rest)
    subset_service = SubsetService(tm1_rest)
    view_service = ViewService(tm1_rest)

    # regular expression for everything that starts with 'temp_' or 'test_'
    regex_list = ['^temp_.*', '^test_.*']

    # iterate through cubes
    cubes = cube_service.get_all_names()
    for cube in cubes:
        private_views, public_views = view_service.get_all(cube_name=cube)
        for view in private_views:
            for regex in regex_list:
                if re.match(regex, view.name, re.IGNORECASE):
                    view_service.delete(cube_name=cube, view_name=view.name, private=True)
        for view in public_views:
            for regex in regex_list:
                if re.match(regex, view.name, re.IGNORECASE):
                    view_service.delete(cube_name=cube, view_name=view.name, private=False)

    # iterate through dimensions
    dimensions = dimension_service.get_all_names()
    for dimension in dimensions:
        subsets = subset_service.get_all_names(dimension_name=dimension, hierarchy_name=dimension)
        for subset in subsets:
            for regex in regex_list:
                if re.match(regex, subset, re.IGNORECASE):
                    subset_service.delete(dimension, subset)
