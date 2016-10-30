from TM1py import TM1pyQueries as TM1, TM1pyLogin
import random
login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get random dimension from the model
    dimension_names = tm1.get_all_dimension_names()
    random_number = random.randint(1, len(dimension_names))
    dimension = tm1.get_dimension(dimension_name=dimension_names[random_number])

    # iterate through hierarchies
    for hierarchy in dimension:
        # iterate through Elements in hierarchy
        for element in hierarchy:
            print('Element Name: {} Index: {} Type: {}'.format(element.name, str(element.index), element.element_type))
        # iterate through Subsets
        for subset in hierarchy.subsets:
            print('Subset Name: {}'.format(subset))
        # iterate through Edges
        for edge in hierarchy.edges:
            print("Parent Name: {}, Component Name: {}".format(edge.parent_name, edge.component_name))

        # print the default member
        print('Default Member: {}'.format(hierarchy.default_member))
