from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.UserService import UserService


login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    user_service = UserService(tm1_rest)
    # Get existing ADMIN
    u = user_service.get('admin')

    # Edit it
    u.name = 'Han Solo'
    u.friendly_name = 'Han'
    u.password = 'MilleniumFalcon'
    u.add_group('Resistance')

    # Create new user on TM1 Server
    user_service.create(u)
