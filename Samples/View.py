from TM1py import TM1Queries as TM1, MDXView
import uuid

# establish connection to TM1 Server
tm1 = TM1(ip='', port=8001, user='admin', password='apple', ssl=False)

# random text
random_string = str(uuid.uuid4())

# create mdx view
mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
      "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
      "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
mdx_view = MDXView(cube_name='plan_BudgetPlan',view_name='TM1py_' + random_string,MDX=mdx)

# create mdx view on TM1 Server
tm1.create_view(view=mdx_view)

# get view content
content = tm1.get_view_content_structured(cube_name=mdx_view.get_cube(),
                                          view_name=mdx_view.get_name())
print(content)

# logout
tm1.logout()

