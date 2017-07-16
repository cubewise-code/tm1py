from Services.RESTService import RESTService
from Services.UserService import UserService
from Services.LoginService import LoginService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    user_service = UserService(tm1_rest)
    u = user_service.get('Great Panda')
    u.friendly_name = 'Panda'
    u.password = 'Bamboo'
    u.add_group('Mammals')
    u.add_group('Bears')
    u.remove_group('Admin')
    user_service.update(u)
