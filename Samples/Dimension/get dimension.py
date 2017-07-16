import random

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.DimensionService import DimensionService

login = LoginService.native('admin', 'apple')

# Connection to TM1. Needs IP, Port, Credentials, and SSL
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    dimension_service = DimensionService(tm1_rest)

    # get random dimension from the model
    dimension_names = dimension_service.get_all_names()
    random_number = random.randint(1, len(dimension_names))
    dimension = dimension_service.get(dimension_name=dimension_names[random_number])

    # iterate through hierarchies
    for hierarchy in dimension:
        print('Hierarchy Name: {}'.format(hierarchy.name))
        # iterate through Elements in hierarchy
        for element in hierarchy:
            print('Element Name: {} Index: {} Type: {}'.format(element.name, str(element.index), element.element_type))
        # iterate through Subsets
        for subset in hierarchy.subsets:
            print('Subset Name: {}'.format(subset))
        # iterate through Edges
        for parent, child in hierarchy.edges:
            print("Parent Name: {}, Component Name: {}".format(parent, child))

        # print the default member
        print('Default Member: {}'.format(hierarchy.default_member))
