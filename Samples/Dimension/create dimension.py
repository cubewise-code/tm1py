from TM1py import TM1pyQueries as TM1, TM1pyLogin, Dimension, Hierarchy, Element, Edge, ElementAttribute

# login object
login = TM1pyLogin.native('admin', 'apple')

name = 'TM1py Region'

# Connection to TM1. Needs IP, Port, Credentials, and SSL
with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # create elements objects
    elements = [Element(name='Europe', element_type='Consolidated'),
                Element(name='CH', element_type='Numeric'),
                Element(name='UK', element_type='Numeric'),
                Element(name='BE', element_type='Numeric')]

    # create edge object
    edges = [Edge(parent_name='Europe', component_name='CH', weight=1),
             Edge(parent_name='Europe', component_name='UK', weight=1),
             Edge(parent_name='Europe', component_name='BE', weight=1)]

    # create the element_attributes
    element_attributes = [ElementAttribute(name='Name Long', attribute_type='Alias'),
                          ElementAttribute(name='Name Short', attribute_type='Alias'),
                          ElementAttribute(name='Currency', attribute_type='String')]

    # create hierarchy object
    hierarchy = Hierarchy(name=name, dimension_name=name, elements=elements, element_attributes=element_attributes,
                          edges=edges)

    # create dimension object
    d = Dimension(name=name, hierarchies=[hierarchy])

    # create dimension in TM1 !
    tm1.create_dimension(d)


