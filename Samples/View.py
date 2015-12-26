from TM1py import TM1Queries, NativeView, MDXView
import uuid

# establish connection to TM1 Server
q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)

# random text
random_string = str(uuid.uuid4())

# create native view
native_view = NativeView(name_cube='plan_Budgetplan', name_view=random_string)

# assign subsets to rows, columns, titles
subset = q.get_subset(dimension_name='plan_version', subset_name='FY 2004 Budget')
native_view.add_row(dimension_name='plan_version', subset=subset)
subset = q.get_subset(dimension_name='plan_business_unit', subset_name='n level business unit')
native_view.add_row(dimension_name='plan_business_unit', subset=subset)
subset = q.get_subset(dimension_name='plan_department', subset_name='n level departments')
native_view.add_row(dimension_name='plan_department', subset=subset)
subset = q.get_subset(dimension_name='plan_chart_of_accounts', subset_name='Consolidations')
native_view.add_row(dimension_name='plan_chart_of_accounts', subset=subset)
subset = q.get_subset(dimension_name='plan_source', subset_name='budget')
native_view.add_row(dimension_name='plan_source', subset=subset)
subset = q.get_subset(dimension_name='plan_exchange_rates', subset_name='actual')
native_view.add_title(dimension_name='plan_exchange_rates', subset=subset, selection='actual')
subset = q.get_subset(dimension_name='plan_time', subset_name='2003 Total Year')
native_view.add_column(dimension_name='plan_time', subset=subset)

# create native view against TM1 Server
q.create_view(view=native_view)

# delete native view from server
q.delete_view(native_view.get_cube(), native_view.get_name())

# random text
random_string = str(uuid.uuid4())

# create mdx view
mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
      "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
      "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
mdx_view = MDXView('plan_Budgetplan', random_string, mdx)

# create mdx view on TM1 Server
q.create_view(view=mdx_view)

# delete mdx view from server
q.delete_view(mdx_view.get_cube(), mdx_view.get_name())

# logout
q.logout()

