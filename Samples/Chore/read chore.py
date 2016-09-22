from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

#read Process:
c = tm1.get_chore('demo')

c._name = 'demo12'
c._start_time.set_time(minute=39)


tm1.create_chore(c)

c._start_time.set_time(minute=49)
c._active = True

tm1.update_chore(c)

#tm1.delete_chore(c._name)


tm1.logout()

