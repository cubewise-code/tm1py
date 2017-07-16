from Services.RESTService import RESTService
from Services.ProcessService import ProcessService
from Services.LoginService import LoginService

from Objects.Process import Process

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    process_name = 'TM1py process'

    # create new Process
    p_ascii = Process(name=process_name,
                      datasource_type='ASCII',
                      datasource_ascii_delimiter_char=',',
                      datasource_data_source_name_for_server=r'C:\Data\file.csv',
                      datasource_data_source_name_for_client=r'C:\Data\file.csv')
    # variables
    p_ascii.add_variable('v_1', 'Numeric')
    p_ascii.add_variable('v_2', 'Numeric')
    p_ascii.add_variable('v_3', 'Numeric')
    p_ascii.add_variable('v_4', 'Numeric')
    # parameters
    p_ascii.add_parameter(name='pCompanyCode', prompt='', value='DE04')
    # code
    p_ascii.prolog_procedure = "sText = 'IBM Cognos TM1';"

    # create process on Server
    process_service = ProcessService(tm1_rest)
    process_service.create(p_ascii)
