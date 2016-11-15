from TM1py import TM1pyLogin, TM1pyQueries as TM1, Edge, Element, Hierarchy, Dimension, ElementAttribute, Cube, Subset

import uuid
import time as t
from datetime import date, time, timedelta, datetime

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

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    for cube in tm1.get_all_cubes():
        if cube.has_rules and cube.rules.has_feeders:
            ti = 'CubeProcessFeeders(\'{}\');'.format(cube.name)
            # process feeders for cube
            tm1.execute_TI_code(lines_prolog=[ti], lines_epilog='')

            # give TM1 a second so that it can write an entry into the messagelog
            t.sleep(1)

            # get logs
            logs = tm1.get_last_message_log_entries(reverse=True, top=10)

            # filter logs
            filtered_logs = (entry for entry in logs if entry['Logger'] == 'TM1.Server' and
                            'TM1CubeImpl::ProcessFeeders:' in entry['Message'] and cube.name in entry['Message'])
            # get start time and end time
            endtime_processing = next(filtered_logs)['TimeStamp']
            starttime_processing = next(filtered_logs)['TimeStamp']

            # determine Delta
            start = get_time_from_tm1_timestamp(starttime_processing)
            end = get_time_from_tm1_timestamp(endtime_processing)
            delta = end-start
            print("Cube: {} | Time for processing Feeders: {}".format(cube.name, delta))
