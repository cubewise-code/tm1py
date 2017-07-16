from Objects.ChoreFrequency import ChoreFrequency

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.ChoreService import ChoreService


# Connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    chore_service = ChoreService(tm1_rest)

    # Read chore:
    c = chore_service.get('real chore')

    # Update properties
    c.reschedule(minutes=-3)
    c._frequency = ChoreFrequency(days=7, hours=22, minutes=5, seconds=1)
    c._execution_mode = 'MultipleCommit'
    c.activate()

    # Update the TM1 chore
    chore_service.update(c)


