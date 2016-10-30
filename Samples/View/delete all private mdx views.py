from TM1py import TM1pyLogin, TM1pyQueries as TM1, MDXView

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    private_views, public_views = tm1.get_all_views("Plan_BudgetPlan")
    for v in private_views:
        if isinstance(v, MDXView):
            tm1.delete_view(cube_name="Plan_BudgetPlan", view_name=v.name, private=True)




