from TM1py.Services import LoginService
from TM1py.Services import ProcessService
from TM1py.Services import RESTService

# connect to TM1 source instance
tm1_source = RESTService(ip='', port=8001, login=LoginService.native('admin', 'apple'), ssl=False)

# connect to TM1 target instance
tm1_target = RESTService(ip='', port=32893, login=LoginService.native('admin', 'apple'), ssl=False)

# read process from source
process_service_source = ProcessService(tm1_source)
p = process_service_source.get('TM1py process')

process_service_target = ProcessService(tm1_target)
# create/update process on target instance
if p.name in process_service_target.get_all_names():
    process_service_target.update(p)
else:
    process_service_target.create(p)

tm1_source.logout()
tm1_target.logout()
