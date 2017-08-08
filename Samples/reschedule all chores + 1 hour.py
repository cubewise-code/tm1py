from TM1py.Services import ChoreService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    chore_service = ChoreService(tm1_rest)
    # Get all chores and update them
    for chore in chore_service.get_all():
        chore.reschedule(hours=-1)
        chore_service.update(chore)





