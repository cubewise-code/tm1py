from TM1py.Services import TM1Service
from TM1py.Objects import Cube

with TM1Service(address='', port=8001, user='admin', password='apple', ssl=False) as tm1:

    c = Cube("dasdasd", ['yellow', 'red'])

    tm1.cubes.create(c)

    tm1.cubes.views()
    c = tm1.cubes(GL)

    tm1.cubes