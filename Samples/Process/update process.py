from Services.RESTService import RESTService
from Services.ProcessService import ProcessService
from Services.LoginService import LoginService

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    #read
    process_service = ProcessService(tm1_rest)
    p = process_service.get('TM1py process')

    # modify
    p.datasource_type = 'None'
    p.epilog_procedure = "nRevenue = 100000;\r\nsCostCenter = 'UK01';"
    p.remove_parameter('pCompanyCode')
    p.add_parameter('pBU', prompt='', value='UK02')

    # update
    process_service.update(p)

