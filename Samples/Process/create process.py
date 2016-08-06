from TM1py import TM1pyQueries as TM1, TM1pyLogin, Process
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# just a random string
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
p_ascii.add_parameter(name='CompanyCode', prompt='', value='DE04')

# create process on Server
tm1.create_process(p_ascii)

# logout
tm1.logout()
