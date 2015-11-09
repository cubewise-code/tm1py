from TM1py import TM1Queries, NativeView, MDXView
import uuid

# establish connection to TM1 Server
q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)

# create native view
random_string = str(uuid.uuid4())
view = NativeView('plan_Budgetplan', random_string)
view.add_row('plan_version', 'FY 2004 Budget')
view.add_row('plan_business_unit', 'n level business unit')
view.add_row('plan_department', 'n level departments')
view.add_row('plan_chart_of_accounts', 'Consolidations')
view.add_title('plan_exchange_rates', 'actual', 'actual')
view.add_row('plan_source', 'budget')
view.add_column('plan_time', '2003 Total Year')
# post native view against TM1 Server
q.create_view(view)


# delete view from server
q.delete_view(view.get_cube(), view.get_name())


# create mdx view
random_string = str(uuid.uuid4())
mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
      "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
      "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
mdx_view = MDXView('plan_Budgetplan', random_string, mdx)
# post mdx view against TM1 Server
q.create_view(mdx_view)


# delete view from server
q.delete_view(mdx_view.get_cube(), mdx_view.get_name())


# logout
q.logout()

