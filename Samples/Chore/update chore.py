from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore, ChoreFrequency
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# read chore:
c = tm1.get_chore('real chore')

# update properties
c.reschedule(minutes=-3)
c._frequency = ChoreFrequency(days=7, hours=22, minutes=5, seconds=1)
c._execution_mode = 'MultipleCommit'
c.activate()

# update the TM1 chore
tm1.update_chore(c)

# logout
tm1.logout()

