from TM1py import TM1pyQueries as TM1, TM1pyLogin, Chore, ChoreFrequency, ChoreTask, ChoreStartTime
import uuid
from datetime import datetime, date, time

# connection to TM1 Server
login = TM1pyLogin.native('admin', 'apple')
tm1 = TM1(ip='', port=8001, login=login, ssl=False)


now = datetime.now()
frequency = ChoreFrequency(days='7', hours='9',minutes='2', seconds='45')
tasks = [ChoreTask(0, 'import_actuals', parameters=[{'Name': 'region', 'Value': 'UK'}])]


c = Chore(name='TM1py_' + str(uuid.uuid4()),
          start_time=ChoreStartTime(now.year, now.month, now.day, now.hour, now.minute, now.second),
          dst_sensitivity=False,
          active=True,
          execution_mode='SingleCommit',
          frequency=frequency,
          tasks=tasks)


tm1.create_chore(c)


tm1.logout()