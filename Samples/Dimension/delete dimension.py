from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.DimensionService import DimensionService


name = 'TM1py Region'

login = LoginService.native('admin', 'apple')

# Connection to TM1. Needs IP, Port, Credentials, and SSL
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    dimension_service = DimensionService(tm1_rest)
    dimension_service.delete(name)


