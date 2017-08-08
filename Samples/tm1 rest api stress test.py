import asyncio

from TM1py.Services import DataService
from TM1py.Services import DimensionService
from TM1py.Services import InfoService
from TM1py.Services import LoginService
from TM1py.Services import ProcessService
from TM1py.Services import RESTService


# define functions
def get_server_name(tm1):
    for i in range(1000):
        data = tm1.get_server_name()

def get_product_version(tm1):
    for i in range(1000):
        data = tm1.get_product_version()

def get_all_dimension_names(tm1):
    for i in range(1000):
        data = tm1.get_all_names()

def get_all_process_names(tm1):
    for i in range(1000):
        data = tm1.get_all_names()

def read_pnl(tm1):
    for i in range(1000):
        data = tm1.get_view_content('Plan_BudgetPlan', 'High Level Profit and Loss', private=False)

# fire requests asynchronously
async def main():
    loop = asyncio.get_event_loop()
    tm1_rest = RESTService('', 8001, LoginService.native('admin', 'apple'), ssl=False)
    info_service = InfoService(tm1_rest)
    dimension_service = DimensionService(tm1_rest)
    process_service = ProcessService(tm1_rest)
    data_service = DataService(tm1_rest)

    future1 = loop.run_in_executor(None, get_product_version, info_service)
    future2 = loop.run_in_executor(None, get_server_name, info_service)
    future3 = loop.run_in_executor(None, read_pnl, data_service)
    future4 = loop.run_in_executor(None, get_all_dimension_names, dimension_service)
    future5 = loop.run_in_executor(None, get_all_process_names, process_service)
    response1, response, response3, response4, response5 = \
        await future1, await future2, await future3, await future4, await future5
    tm1_rest.logout()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
