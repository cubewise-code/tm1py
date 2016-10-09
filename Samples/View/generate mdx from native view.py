from TM1py import TM1pyQueries as TM1, TM1pyLogin, MDXView

# establish connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)

# instantiate TM1py.NativeView object
nv = tm1.get_native_view('Plan_BudgetPlan','High Level Profit And Loss')

# retrieve MDX from native view. print it
print(nv.as_MDX)

# logout
tm1.logout()
