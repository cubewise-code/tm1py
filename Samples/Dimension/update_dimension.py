from TM1py import TM1pyQueries as TM1, TM1pyLogin, Edge

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    dimension = tm1.get_dimension('plan_department')

    h = dimension.hierarchies[0]
    #h.add_element(element_name='TM1py Elem',element_type='Consolidated')

    h.add_edge(edge=Edge(parent_name='TM1py elem', component_name='1000', weight=1000))

    print(h.body)

    tm1.update_hierarchy(h)