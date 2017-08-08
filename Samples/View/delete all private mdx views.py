from TM1py.Objects import MDXView
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import ViewService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    view_service = ViewService(tm1_rest)

    private_views, public_views = view_service.get_all("Plan_BudgetPlan")
    for v in private_views:
        if isinstance(v, MDXView):
            view_service.delete(cube_name="Plan_BudgetPlan", view_name=v.name, private=True)




