from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    c = tm1.get_cube('Plan_BudgetPlan')
    print(c.name)
    print(c.dimensions)
    print(c.rules.has_skipcheck)