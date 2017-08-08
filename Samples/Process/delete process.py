from TM1py.Services import LoginService
from TM1py.Services import ProcessService
from TM1py.Services import RESTService

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # delete Process:
    process_service = ProcessService(tm1_rest)
    process_service.delete('TM1py process')

