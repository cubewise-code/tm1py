from Services.RESTService import RESTService
from Services.ViewService import ViewService
from Services.LoginService import LoginService


login = LoginService.native('admin', 'apple')

# establish connection to TM1 Server
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:

    # instantiate TM1py.NativeView object
    view_service = ViewService(tm1_rest)
    nv = view_service.get_native_view('Plan_BudgetPlan', 'High Level Profit And Loss', private=False)

    # retrieve MDX from native view. print it
    print(nv.as_MDX)
