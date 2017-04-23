from TM1py import TM1pyQueries as TM1, TM1pyLogin

# connect to TM1 source instance
tm1_source = TM1(ip='', port=8001, login=TM1pyLogin.native('admin', 'apple'), ssl=False)

# connect to TM1 target instance
tm1_target = TM1(ip='', port=8034, login=TM1pyLogin.native('admin', 'apple'), ssl=True)

# read process from source
p = tm1_source.get_process('TM1py process')

# create process on target instance
tm1_target.create_process(p)

# explicit logout, since HTTPSessionTimeoutMinutes doesnt work (FP < 5)
tm1_source.logout()
tm1_target.logout()
