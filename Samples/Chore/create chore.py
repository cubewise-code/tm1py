from Objects.Chore import Chore
from Objects.ChoreFrequency import ChoreFrequency
from Objects.ChoreStartTime import ChoreStartTime
from Objects.ChoreTask import ChoreTask

from Services.LoginService import LoginService
from Services.RESTService import RESTService
from Services.ChoreService import ChoreService

import uuid
from datetime import datetime

# connection to TM1 Server
login = LoginService.native('admin', 'apple')
with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    now = datetime.now()
    frequency = ChoreFrequency(days='7', hours='9', minutes='2', seconds='45')
    tasks = [ChoreTask(0, 'import_actuals', parameters=[{'Name': 'pRegion', 'Value': 'UK'}])]

    c = Chore(name='TM1py_' + str(uuid.uuid4()),
              start_time=ChoreStartTime(now.year, now.month, now.day, now.hour, now.minute, now.second),
              dst_sensitivity=False,
              active=True,
              execution_mode='SingleCommit',
              frequency=frequency,
              tasks=tasks)

    chore_service = ChoreService(tm1_rest)
    chore_service.create(c)
