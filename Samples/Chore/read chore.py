from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

#read Process:
c = tm1.get_chore('real chore')

# print out processes and parameters
for task in c._tasks:
    print("Process: {} Parameters: {}".format(task._process_name, task._parameters))

# logout
tm1.logout()

