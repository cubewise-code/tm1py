from TM1py import TM1pyQueries as TM1, TM1pyLogin, Edge
import uuid

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:

    # get dimension
    dimension = tm1.get_dimension('plan_department')

    # get the default hierarchy of the dimension
    h = dimension.hierarchies[0]

    # create new random element name
    element_name = str(uuid.uuid4())

    # add element to hierarchy
    h.add_element(element_name=element_name, element_type='Numeric')

    # add edge to hierarchy
    h.add_edge(edge=Edge(parent_name='TM1py elem', component_name=element_name, weight=1000))

    # write Hierarchy back to TM1
    tm1.update_hierarchy(h)