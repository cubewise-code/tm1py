""" Requires Python 3.5 or greater

"""

import asyncio

from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.ProcessService import ProcessService


regions = ['DE', 'UK', 'US', 'BE', 'AU', 'JP', 'CN', 'NZ', 'FR', 'PL']
process = 'import_actuals'


# Define Function
def run_process(process_service, region):
    print("run process with parameter pRegion: " + region)
    parameters = {
        'Parameters': [{
            'Name': "pRegion",
            'Value': region
        }]
    }
    process_service.execute(process, parameters)
    print("Done running Process for Region : " + region)

# Fire requests asynchronously
async def main():
    loop = asyncio.get_event_loop()
    with RESTService('', 8001, LoginService.native('admin', 'apple'), ssl=False) as tm1_rest:
        process_service = ProcessService(tm1_rest)
        futures = [loop.run_in_executor(None, run_process, process_service, 'pRegion ' + regions[num])
                   for num
                   in range(1, 10)]
        for future in futures:
            await future

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
