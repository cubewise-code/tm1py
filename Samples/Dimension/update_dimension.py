import uuid

from TM1py.Services import DimensionService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

# Connection to TM1. Needs IP, Port, Credentials, and SSL
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    dimension_service = DimensionService(tm1_rest)

    # get dimension
    dimension = dimension_service.get('plan_department')

    # get the default hierarchy of the dimension
    h = dimension.hierarchies[0]

    # create new random element name
    element_name = str(uuid.uuid4())

    # add element to hierarchy
    h.add_element(element_name=element_name, element_type='Numeric')

    # add edge to hierarchy
    h.add_edge('TM1py elem', element_name, 1000)

    # write Hierarchy back to TM1
    dimension_service.update(dimension)
