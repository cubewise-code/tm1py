from TM1py.Objects import Cube
from TM1py.Services import CubeService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    cube = Cube(name='Rubiks Cube', dimensions=['red', 'green', 'blue', 'yellow'], rules='')
    cube_service.create(cube)
