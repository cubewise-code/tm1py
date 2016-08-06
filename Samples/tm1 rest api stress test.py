from TM1py import TM1pyQueries as TM1, TM1pyLogin

# login
tm1 = TM1('', 8001, TM1pyLogin.native('admin', 'apple'), ssl=False)

# fire asynchronous requests


# logout
tm1.logout()
