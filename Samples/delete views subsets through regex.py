from TM1py import TM1pyQueries as TM1, TM1pyLogin
import re

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:

    # regular expression for everything that starts with 'temp_'
    regex_pattern = '^temp_.*'

    # iterate through cubes
    cubes = tm1.get_all_cube_names()
    for cube in cubes:
        private_views, public_views = tm1.get_all_views(cube_name=cube)
        for view in private_views:
            if re.match(regex_pattern, view.name.lower()):
                tm1.delete_view(cube_name=cube, view_name=view.name, private=True)
        for view in public_views:
            if re.match(regex_pattern, view.name.lower()):
                tm1.delete_view(cube_name=cube, view_name=view.name, private=False)

    # iterate through dimensions
    dimensions = tm1.get_all_dimension_names()
    for dimension in dimensions:
        subsets = tm1.get_all_subset_names(dimension_name=dimension, hierarchy_name=dimension)
        for subset in subsets:
            if re.match(regex_pattern, subset.lower()):
                tm1.delete_subset(dimension, subset)
