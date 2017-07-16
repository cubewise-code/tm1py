import time as t
from datetime import date, time, datetime

from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.CubeService import CubeService
from Services.ProcessService import ProcessService
from Services.InfoService import InfoService


# time magic with python
def get_time_from_tm1_timestamp(tm1_timestamp):
    f = lambda x: int(x) if x else 0
    year = f(tm1_timestamp[0:4])
    month = f(tm1_timestamp[5:7])
    day = f(tm1_timestamp[8:10])
    hour = f(tm1_timestamp[11:13])
    minute = f(tm1_timestamp[14:16])
    second = f(tm1_timestamp[17:19])
    return datetime.combine(date(year, month, day), time(hour, minute, second))


login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    cube_service = CubeService(tm1_rest)
    process_service = ProcessService(tm1_rest)
    info_service = InfoService(tm1_rest)

    for cube in cube_service.get_all():
        if cube.has_rules and cube.rules.has_feeders:
            ti = 'CubeProcessFeeders(\'{}\');'.format(cube.name)
            # Process feeders for cube
            process_service.execute_ti_code(lines_prolog=[ti], lines_epilog='')

            # Give TM1 a second so that it can write an entry into the messagelog
            t.sleep(1)

            # Get logs
            logs = info_service.get_last_message_log_entries(reverse=True, top=10)

            # Filter logs
            filtered_logs = (entry for entry
                             in logs
                             if entry['Logger'] == 'TM1.Server' and 'TM1CubeImpl::ProcessFeeders:' in entry['Message']
                             and cube.name in entry['Message'])

            # Get start time and end time
            endtime_processing = next(filtered_logs)['TimeStamp']
            starttime_processing = next(filtered_logs)['TimeStamp']

            # Calculate Delta
            start = get_time_from_tm1_timestamp(starttime_processing)
            end = get_time_from_tm1_timestamp(endtime_processing)
            delta = end-start
            print("Cube: {} | Time for processing Feeders: {}".format(cube.name, delta))
