import pickle


from TM1py.Services import HierarchyService, SecurityService, ApplicationService, SubsetService, \
     ProcessService, AnnotationService, ViewService, RestService, CellService, \
     ChoreService, DimensionService, CubeService, ElementService, SandboxService, GitService
from TM1py.Services.FileService import FileService
from TM1py.Services.JobService import JobService
from TM1py.Services.UserService import UserService
from TM1py.Services.ThreadService import ThreadService
from TM1py.Services.SessionService import SessionService
from TM1py.Services.TransactionLogService import TransactionLogService
from TM1py.Services.MessageLogService import MessageLogService
from TM1py.Services.ConfigurationService import ConfigurationService
from TM1py.Services.AuditLogService import AuditLogService
from TM1py.Services.LoggerService import LoggerService

from TM1py.Services.PowerBiService import PowerBiService
from TM1py.Services.ServerService import ServerService
from TM1py.Services.MonitoringService import MonitoringService

class TM1Service:
    """ All features of TM1py are exposed through this service
    
    Can be saved and restored from File, to avoid multiple authentication with TM1.
    """

    def __init__(self, **kwargs):
        """ Initiate the TM1Service

        :param address: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param base_url - base url e.g. https://localhost:12354/api/v1
        :param user: String - name of the user
        :param password String - password of the user
        :param decode_b64 - whether password argument is b64 encoded
        :param namespace String - optional CAM namespace
        :param ssl: boolean -  as specified in the tm1s.cfg
        :param cam_passport: String - the cam passport
        :param session_id: String - TM1SessionId e.g. q7O6e1w49AixeuLVxJ1GZg
        :param session_context: String - Name of the Application. Controls "Context" column in Arc / TM1top.
                If None, use default: TM1py
        :param verify: path to .cer file or 'True' / True / 'False' / False (if no ssl verification is required)
        :param logging: boolean - switch on/off verbose http logging into sys.stdout
        :param timeout: Float - Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param async_requests_mode: changes internal REST execution mode to avoid 60s timeout on IBM cloud
        :param connection_pool_size - In a multi threaded environment, you should set this value to a
                higher number, such as the number of threads
        :param integrated_login: True for IntegratedSecurityMode3
        :param integrated_login_domain: NT Domain name.
                Default: '.' for local account.
        :param integrated_login_service: Kerberos Service type for remote Service Principal Name.
                Default: 'HTTP'
        :param integrated_login_host: Host name for Service Principal Name.
                Default: Extracted from request URI
        :param integrated_login_delegate: Indicates that the user's credentials are to be delegated to the server.
                Default: False
        :param impersonate: Name of user to impersonate
        :param re_connect_on_session_timeout: attempt to reconnect once if session is timed out
        :param proxies: pass a dictionary with proxies e.g.
                {'http': 'http://proxy.example.com:8080', 'https': 'http://secureproxy.example.com:8090'}
        """
        self._tm1_rest = RestService(**kwargs)
        self.annotations = AnnotationService(self._tm1_rest)
        self.cells = CellService(self._tm1_rest)
        self.chores = ChoreService(self._tm1_rest)
        self.cubes = CubeService(self._tm1_rest)
        self.dimensions = DimensionService(self._tm1_rest)
        self.elements = ElementService(self._tm1_rest)
        self.git = GitService(self._tm1_rest)
        self.hierarchies = HierarchyService(self._tm1_rest)
        self.processes = ProcessService(self._tm1_rest)
        self.security = SecurityService(self._tm1_rest)
        self.subsets = SubsetService(self._tm1_rest)
        self.applications = ApplicationService(self._tm1_rest)
        self.views = ViewService(self._tm1_rest)
        self.sandboxes = SandboxService(self._tm1_rest)
        self.files = FileService(self._tm1_rest)
        self.jobs = JobService(self._tm1_rest)
        self.users = UserService(self._tm1_rest)
        self.threads = ThreadService(self._tm1_rest)
        self.sessions = SessionService(self._tm1_rest)
        self.transaction_logs = TransactionLogService(self._tm1_rest)
        self.message_logs = MessageLogService(self._tm1_rest)
        self.configuration = ConfigurationService(self._tm1_rest)
        self.audit_logs = AuditLogService(self._tm1_rest)

        #higher level modules
        self.server = ServerService(self._tm1_rest)
        self.monitoring = MonitoringService(self._tm1_rest)
        self.power_bi = PowerBiService(self._tm1_rest)
        self.loggers = LoggerService(self._tm1_rest)

    def logout(self, **kwargs):
        self._tm1_rest.logout(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    @property
    def whoami(self):
        return self.security.get_current_user()

    @property
    def metadata(self):
        return self._tm1_rest.get_api_metadata()

    @property
    def version(self):
        return self._tm1_rest.version

    @property
    def connection(self):
        return self._tm1_rest

    def save_to_file(self, file_name):
        with open(file_name, 'wb') as file:
            pickle.dump(self, file)

    @classmethod
    def restore_from_file(cls, file_name):
        with open(file_name, 'rb') as file:
            return pickle.load(file)

    def re_authenticate(self):
        self._tm1_rest.connect()

    def re_connect(self):
        self._tm1_rest.connect()
