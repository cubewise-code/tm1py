import json
import os

tm1_connection = os.environ.get('TM1_CONNECTION')
tm1_connection_secret = os.environ.get('TM1_CONNECTION_SECRET')

config_content = '[tm1srv01]\n'

if tm1_connection:
    conn_data = json.loads(tm1_connection)
    for key, value in conn_data.items():
        config_content += f"{key}={value}\n"

if tm1_connection_secret:
    secret_data = json.loads(tm1_connection_secret)
    for key, value in secret_data.items():
        config_content += f"{key}={value}\n"

with open('Tests/config.ini', 'w') as f:
    f.write(config_content)