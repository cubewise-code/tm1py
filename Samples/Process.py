from TM1py import TM1pyQueries as TM1, Process
import uuid

# connection to TM1 Server
tm1 = TM1(ip='localhost', port=8001, user='admin', password='apple', ssl=False)

# just a random string
random_string = str(uuid.uuid4())

# create new Process
p_ascii = Process(name='sample_ascii_' + random_string,
                  datasource_type='ASCII',
                  datasource_ascii_delimiter_char=',',
                  datasource_data_source_name_for_server='C:\Data\just_a_file.csv',
                  datasource_data_source_name_for_client='C:\Data\just_a_file.csv')

# variables
p_ascii.add_variable('v_1', 'Numeric')
p_ascii.add_variable('v_2', 'Numeric')
p_ascii.add_variable('v_3', 'Numeric')
p_ascii.add_variable('v_4', 'Numeric')

# parameters
p_ascii.add_parameter(name='CompanyCode', prompt='', value='DE04')

# create process on Server
tm1.create_process(p_ascii)

# update existing Process:
p_new = tm1.get_process(p_ascii.name)

# modify
p_new.set_data_procedure(Process.auto_generated_string() + "a = 2;")

# update on Server
tm1.update_process(p_new)

# delete Process from Server
tm1.delete_process(p_new.name)

# logout
tm1.logout()
