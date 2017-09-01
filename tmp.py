from TM1py.Services import TM1Service
from TM1py.Objects import Hierarchy

with TM1Service(address='', port=12354, user='admin', password='apple', ssl=True) as tm1:

    print(tm1.dimensions.get('plan_department'))


    """
    dimension = tm1.dimensions.get('plan_department')
    elements = list(dimension.default_hierarchy.elements.values())
    new_hierarchy = Hierarchy('new Hierarchy 2', 'plan_department', elements, edges=dimension.default_hierarchy.edges)
    tm1.dimensions.hierarchies.create(new_hierarchy)
    """

    #element_selections = 'FY 2004 Budget, UK, plan_department::Direct&&Leaves::Direct, Revenue, local, input, Dec-2004'
    #print(tm1.cubes.cells.get_value("Plan_BudgetPlan", element_selections))

    #s = Subset('new subs', 'plan_department', hierarchy_name='Leaves', elements=['110', '105'])
    #tm1.dimensions.subsets.create(s, False)
