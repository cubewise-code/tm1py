from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

# connection to TM1 Server
with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get all chores and update them
    for chore in tm1.get_all_chores():
        chore.reschedule(hours=-1)
        tm1.update_chore(chore)





