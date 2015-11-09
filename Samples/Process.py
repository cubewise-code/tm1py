from TM1py import TM1Queries, Process
import uuid

# connection to TM1 Server
q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)
# just a random string
random_string = str(uuid.uuid4()).replace('-', '_')

# create new Process
p_ascii = Process(name='unittest_ascii_' + random_string, datasource_type='ASCII',
                  datasource_ascii_delimiter_char=',',
                  datasource_data_source_name_for_server='C:\Data\simple_csv.csv',
                  datasource_data_source_name_for_client='C:\Data\simple_csv.csv')
# variables
p_ascii.add_variable('v_1', 'Numeric')
p_ascii.add_variable('v_2', 'Numeric')
p_ascii.add_variable('v_3', 'Numeric')
p_ascii.add_variable('v_4', 'Numeric')
# parameters
p_ascii.add_parameter('p_Year', 'year?', '2016')
# create process on Server
q.create_process(p_ascii)

# update existing Process:
p_new = q.get_process(p_ascii.name)
# modify
p_new.set_data_procedure(Process.auto_generated_string() + "x = 'Hi this is a test';")
# update on Server
q.update_process(p_new)

# delete Process from Server
q.delete_process(p_new.name)

# logout
q.logout()
