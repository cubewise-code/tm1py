from TM1py.Services import ChoreService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    chore_service = ChoreService(tm1_rest)
    # read Chore:
    chores = chore_service.get_all()

    # delete the TM1py Chores
    for chore in chores:
        if 'TM1py' in chore.name:
            chore_service.delete(chore.name)


