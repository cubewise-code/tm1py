import asyncio

from TM1py.Services import DataService
from TM1py.Services import LoginService
from TM1py.Services import RESTService

# mdx Queries
mdx1 = "SELECT {[plan_version].MEMBERS}*{[plan_chart_of_accounts].Members} * {[plan_exchange_rates].Members}  on COLUMNS, {[plan_business_unit].MEMBERS}*{[plan_department].MEMBERS} on ROWS FROM [plan_BudgetPlan]WHERE ([plan_source].[input], [plan_time].[Jun-2004] )"
mdx2 = "SELECT {[plan_version].MEMBERS}*{[plan_chart_of_accounts].Members} * {[plan_exchange_rates].Members}  on COLUMNS, {[plan_business_unit].MEMBERS}*{[plan_department].MEMBERS} on ROWS FROM [plan_BudgetPlan]WHERE ([plan_source].[input], [plan_time].[Jun-2004] )"
mdx3 = "SELECT {[plan_version].MEMBERS}*{[plan_chart_of_accounts].Members} * {[plan_exchange_rates].Members}  on COLUMNS, {[plan_business_unit].MEMBERS}*{[plan_department].MEMBERS} on ROWS FROM [plan_BudgetPlan]WHERE ([plan_source].[input], [plan_time].[Jun-2004] )"
mdx4 = "SELECT {[plan_version].MEMBERS}*{[plan_chart_of_accounts].Members} * {[plan_exchange_rates].Members}  on COLUMNS, {[plan_business_unit].MEMBERS}*{[plan_department].MEMBERS} on ROWS FROM [plan_BudgetPlan]WHERE ([plan_source].[input], [plan_time].[Jun-2004] )"
mdx5 = "SELECT {[plan_version].MEMBERS}*{[plan_chart_of_accounts].Members} * {[plan_exchange_rates].Members}  on COLUMNS, {[plan_business_unit].MEMBERS}*{[plan_department].MEMBERS} on ROWS FROM [plan_BudgetPlan]WHERE ([plan_source].[input], [plan_time].[Jun-2004] )"


# Define function
def execute_mdx(data_service, mdx):
    for i in range(20):
        data_service.execute_mdx(mdx)

# Fire requests asynchronously
async def main():
    loop = asyncio.get_event_loop()
    with RESTService('', 8001, LoginService.native('admin', 'apple'), ssl=False) as tm1_rest:
        data_service = DataService(tm1_rest)

        future1 = loop.run_in_executor(None, execute_mdx, data_service, mdx1)
        future2 = loop.run_in_executor(None, execute_mdx, data_service, mdx2)
        future3 = loop.run_in_executor(None, execute_mdx, data_service, mdx3)
        future4 = loop.run_in_executor(None, execute_mdx, data_service, mdx4)
        future5 = loop.run_in_executor(None, execute_mdx, data_service, mdx5)
        response1, response, response3, response4, response5 = \
            await future1, await future2, await future3, await future4, await future5


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
