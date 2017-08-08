from TM1py.Objects import Rules
from TM1py.Services import CubeService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    cube = cube_service.get('Rubiks Cube')
    rules = Rules("SKIPCHECK;\n['red':'e1'] = N: 1;")
    cube.rules = rules
    cube_service.update(cube)

