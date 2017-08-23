from TM1py.Services import TM1Service

with TM1Service(address='', port=8001, user='admin', password='apple', ssl=True) as tm1:
    messages = tm1.server.get_last_message_log_entries(reverse=True, top=100)
    print(messages)