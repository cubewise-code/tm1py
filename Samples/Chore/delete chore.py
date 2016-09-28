from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore, ChoreFrequency
import uuid

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# read Chore:
chores = tm1.get_all_chores()

# delete the TM1py Chores
for chore in chores:
    if 'TM1py' in chore._name:
        tm1.delete_chore(chore._name)

# logout
tm1.logout()

