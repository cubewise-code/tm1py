from TM1py.Services import LoginService
from TM1py.Services import ProcessService
from TM1py.Services import RESTService

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # read Process
    process_service = ProcessService(tm1_rest)
    p = process_service.get('TM1py process')

    # print variables, parameters, ...
    print('Parameters: \r\n' + str(p.parameters))
    print('Variables: \r\n' + str(p.variables))
    print('Prolog: \r\n' + str(p.prolog_procedure))
    print('Metadata: \r\n' + str(p.metadata_procedure))
    print('Data: \r\n' + str(p.data_procedure))
    print('Epilog: \r\n' + str(p.epilog_procedure))

