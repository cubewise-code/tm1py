from TM1py import TM1pyQueries as TM1, TM1pyLogin, MDXView
import uuid

# establish connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
      # random text
      random_string = str(uuid.uuid4())

      # create mdx view
      mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
            "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
            "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
      mdx_view = MDXView(cube_name='plan_BudgetPlan', view_name='TM1py_' + random_string, MDX=mdx)

      # create mdx view on TM1 Server
      tm1.create_view(view=mdx_view)

      # get view content
      content = tm1.get_view_content(cube_name=mdx_view.cube, view_name=mdx_view.name)

      # print content
      print(content)



