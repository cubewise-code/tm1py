from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get dimension with all its hierarchies its dependencies
    dimension = tm1.get_dimension('plan_department')

    # iterate through hierarchies
    for hierarchy in dimension:
        # iterate through Elements in hierarchy
        for element in hierarchy:
            attribute_values_text = ''
            for attribute in element.element_attributes:
                attribute_values_text += attribute
            print('Element Name: {} Index: {} Type: {}'.format(element.name, str(element.index), element.element_type))
        # iterate through Subsets
        for subset in hierarchy.subsets:
            print('Subset Name: {}'.format(subset))
        # iterate through Edges
        for edge in hierarchy.edges:
            print("Parent Name: {}, Component Name: {}".format(edge.parent_name, edge.component_name))

        # print the default member
        print('Default Member: {}'.format(hierarchy.default_member))
