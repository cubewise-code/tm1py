from Objects.Rules import Rules

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.CubeService import CubeService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    cube = cube_service.get('Rubiks Cube')
    rules = Rules("SKIPCHECK;\n['red':'e1'] = N: 1;")
    cube.rules = rules
    cube_service.update(cube)

