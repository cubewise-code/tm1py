from TM1py import TM1pyQueries as TM1, TM1pyLogin

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# get all chores and update them
for chore in tm1.get_all_chores():
    chore.reschedule(hours=-1)
    tm1.update_chore(chore)

# logout
tm1.logout()

