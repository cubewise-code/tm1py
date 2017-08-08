from TM1py.Objects import User
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import UserService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    user_service = UserService(tm1_rest)
    u = User(name='Hodor Hodor', friendly_name='Hodor', groups=['Admin'], password='apple')
    user_service.create(u)
