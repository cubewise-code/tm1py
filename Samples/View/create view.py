from TM1py.Objects import NativeView
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import SubsetService
from TM1py.Services import ViewService

login = LoginService.native('admin', 'apple')

# establish connection to TM1 Server
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:

    subset_service = SubsetService(tm1_rest)
    view_service = ViewService(tm1_rest)

    native_view = NativeView(cube_name='Plan_BudgetPlan',
                             view_name='TM1py View2')

    # set up native view - put subsets on Rows, Columns and Titles
    subset = subset_service.get(dimension_name='plan_version', subset_name='FY 2004 Budget', private=False)
    native_view.add_row(dimension_name='plan_version', subset=subset)

    subset = subset_service.get(dimension_name='plan_business_unit', subset_name='n level business unit', private=False)
    native_view.add_row(dimension_name='plan_business_unit', subset=subset)

    subset = subset_service.get(dimension_name='plan_department', subset_name='n level departments', private=False)
    native_view.add_row(dimension_name='plan_department', subset=subset)

    subset = subset_service.get(dimension_name='plan_chart_of_accounts', subset_name='Consolidations', private=False)
    native_view.add_row(dimension_name='plan_chart_of_accounts', subset=subset)

    subset = subset_service.get(dimension_name='plan_exchange_rates', subset_name='local', private=False)
    native_view.add_title(dimension_name='plan_exchange_rates', subset=subset, selection='local')

    subset = subset_service.get(dimension_name='plan_time', subset_name='2004 Total Year', private=False)
    native_view.add_column(dimension_name='plan_time', subset=subset)

    subset = subset_service.get(dimension_name='plan_source', subset_name='budget', private=False)
    native_view.add_column(dimension_name='plan_source', subset=subset)

    # create native view on Server
    view_service.create(view=native_view, private=False)
