from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.ChoreService import ChoreService


# Connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    chore_service = ChoreService(tm1_rest)
    # Read Chore:
    c = chore_service.get('real chore')

    # Print out the tasks
    for task in c.tasks:
        print("Process: {} Parameters: {}".format(task, task.parameters))


