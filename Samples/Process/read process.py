from TM1py import TM1pyQueries as TM1, TM1pyLogin, Process
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

#read Process:
p = tm1.get_process('TM1py process')
print(p.parameters)

tm1.logout()

