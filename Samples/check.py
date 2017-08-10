from TM1py.Services import InfoService, LoginService, RESTService

# Parameters for connection
user = 'admin'
password = 'apple'
ip = ''
port = 8001
ssl = False

login = LoginService.native(user, password)
with RESTService(ip=ip, port=port, login=login, ssl=ssl) as tm1_rest:
    info_service = InfoService(tm1_rest)
    server_name = info_service.get_server_name()
    print(server_name)
