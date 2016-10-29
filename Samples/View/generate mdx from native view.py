from TM1py import TM1pyQueries as TM1, TM1pyLogin, MDXView

login = TM1pyLogin.native('admin', 'apple')

# establish connection to TM1 Server
with TM1(ip='', port=8001, login=login, ssl=False) as tm1:

    # instantiate TM1py.NativeView object
    nv = tm1.get_native_view('Plan_BudgetPlan', 'High Level Profit And Loss')

    # retrieve MDX from native view. print it
    print(nv.as_MDX)
