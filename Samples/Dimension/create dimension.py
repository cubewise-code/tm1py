from TM1py.Objects import Dimension
from TM1py.Objects import Element
from TM1py.Objects import ElementAttribute
from TM1py.Objects import Hierarchy
from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

name = 'TM1py Region'

# Connection to TM1. Needs IP, Port, Credentials, and SSL
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    dimension_service = DimensionService(tm1_rest)

    # create elements objects
    elements = [Element(name='Europe', element_type='Consolidated'),
                Element(name='CH', element_type='Numeric'),
                Element(name='UK', element_type='Numeric'),
                Element(name='BE', element_type='Numeric')]

    # create edge object
    edges = {('Europe', 'CH'): 1,
             ('Europe', 'UK'): 1,
             ('Europe', 'BE'): 1}

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
    dimension_service.create(d)


