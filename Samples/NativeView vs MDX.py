from TM1py import TM1pyLogin, TM1pyQueries as TM1
import time

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    cube_name = 'Plan_BudgetPlan'
    view_name = 'PerformanceTest'

    # extract MDX from CubeView
    mdx = tm1.get_native_view(cube_name, view_name, private=False).MDX

    # Results List
    runtimes_view = []
    runtimes_mdx = []

    # Query data through CubeView
    for i in range(50):
        start_time = time.time()
        a = tm1.get_view_content(cube_name, view_name, private=False)
        a_len =len(a.items())
        run_time = time.time() - start_time
        runtimes_view.append(run_time)

    # Query data through MDX
    for i in range(50):
        start_time = time.time()
        b = tm1.execute_mdx(mdx, cube_name)
        b_len =len(b.items())
        run_time = time.time() - start_time
        runtimes_mdx.append(run_time)

    print("View: " + str(sum(runtimes_view)/len(runtimes_view)))
    print("MDX: " + str(sum(runtimes_mdx) / len(runtimes_mdx)))



