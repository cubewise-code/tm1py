import time

from TM1py.Services import CubeService
from TM1py.Services import DataService
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import ViewService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # Setup services
    cube_service = CubeService(tm1_rest)
    view_service = ViewService(tm1_rest)
    data_service = DataService(tm1_rest)

    cube_name = 'Plan_BudgetPlan'
    view_name = 'PerformanceTest'

    # Extract MDX from CubeView
    mdx = view_service.get_native_view(cube_name, view_name, private=False).MDX

    print(mdx)

    # Results List
    runtimes_view = []
    runtimes_mdx = []

    # Query data through CubeView
    for i in range(10):
        start_time = time.time()
        a = data_service.get_view_content(cube_name, view_name, private=False)
        run_time = time.time() - start_time
        runtimes_view.append(run_time)

    # Query data through MDX
    for j in range(10):
        start_time = time.time()
        b = data_service.execute_mdx(mdx)
        run_time = time.time() - start_time
        runtimes_mdx.append(run_time)

    print("View: " + str(sum(runtimes_view)/len(runtimes_view)))
    print("MDX: " + str(sum(runtimes_mdx) / len(runtimes_mdx)))

    print('Data is the same, right? {}'.format(a == b))


