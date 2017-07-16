from Services.RESTService import RESTService
from Services.UserService import UserService
from Services.LoginService import LoginService
from Objects.User import User

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    user_service = UserService(tm1_rest)
    u = User(name='Hodor Hodor', friendly_name='Hodor', groups=['Admin'], password='apple')
    user_service.create(u)
