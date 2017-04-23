from TM1py import TM1pyQueries as TM1, TM1pyLogin, Process
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# delete Process:
p = tm1.delete_process('TM1py process')

# logout
tm1.logout()

