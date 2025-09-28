import pickle
import warnings

from TM1py.Services import (
    AnnotationService,
    ApplicationService,
    CellService,
    ChoreService,
    CubeService,
    DimensionService,
    ElementService,
    GitService,
    HierarchyService,
    ProcessService,
    RestService,
    SandboxService,
    SecurityService,
    SubsetService,
    ViewService,
)
from TM1py.Services.AuditLogService import AuditLogService
from TM1py.Services.ConfigurationService import ConfigurationService
from TM1py.Services.FileService import FileService
from TM1py.Services.JobService import JobService
from TM1py.Services.LoggerService import LoggerService
from TM1py.Services.MessageLogService import MessageLogService
from TM1py.Services.MonitoringService import MonitoringService
from TM1py.Services.PowerBiService import PowerBiService
from TM1py.Services.ServerService import ServerService
from TM1py.Services.SessionService import SessionService
from TM1py.Services.ThreadService import ThreadService
from TM1py.Services.TransactionLogService import TransactionLogService
from TM1py.Services.UserService import UserService


class TM1Service:
    """All features of TM1py are exposed through this service

    Can be saved and restored from File, to avoid multiple authentication with TM1.

    """

    def __init__(self, **kwargs):
        """Initiate the TM1Service

        Supported kwargs arguments:

        - **address** (str): Address of the TM1 instance.
        - **port** (int): HTTPPortNumber as specified in the tm1s.cfg.
        - **ssl** (bool): Whether to use SSL, as specified in the tm1s.cfg.
        - **instance** (str): Planning Analytics engine (v12) instance name.
        - **database** (str): Planning Analytics engine (v12) database name.
        - **base_url** (str): Base URL for the REST API.
        - **auth_url** (str): Authentication URL for Planning Analytics engine (v12).
        - **user** (str): Name of the user.
        - **password** (str): Password of the user.
        - **decode_b64** (bool): Whether the password argument is Base64 encoded.
        - **namespace** (str): Optional CAM namespace.
        - **cam_passport** (str): The CAM passport.
        - **session_id** (str): TM1SessionId, e.g., "q7O6e1w49AixeuLVxJ1GZg".
        - **application_client_id** (str): Planning Analytics engine (v12) named application client ID.
        - **application_client_secret** (str): Planning Analytics engine (v12) named application secret.
        - **api_key** (str): Planning Analytics engine (v12) API Key.
        - **iam_url** (str): IBM Cloud IAM URL. Default: "https://iam.cloud.ibm.com".
        - **pa_url** (str): Planning Analytics engine (v12) PA URL.
        - **cpd_url** (str): Cloud Pak for Data URL (aka ZEN).
        - **tenant** (str): Planning Analytics engine (v12) tenant.
        - **session_context** (str): Name of the application. Controls "Context" column in Arc/TM1top.
        - **verify** (bool or str): Path to .cer file or boolean for SSL verification.
        - **logging** (bool): Enable or disable verbose HTTP logging.
        - **timeout** (float): Number of seconds to wait for a response.
        - **cancel_at_timeout** (bool): Abort operation in TM1 when timeout is reached.
        - **async_requests_mode** (bool): Enable asynchronous request mode.
        - **connection_pool_size** (int): Maximum number of connections in the pool.
        - **pool_connections** (int): Number of connection pools to cache.
        - **integrated_login** (bool): True for IntegratedSecurityMode3.
        - **integrated_login_domain** (str): NT Domain name.
        - **integrated_login_service** (str): Kerberos Service type for remote Service Principal Name.
        - **integrated_login_host** (str): Host name for Service Principal Name.
        - **integrated_login_delegate** (bool): Delegate user credentials to the server.
        - **impersonate** (str): Name of the user to impersonate.
        - **re_connect_on_session_timeout** (bool): Attempt to reconnect if the session times out.
        - **re_connect_on_remote_disconnect** (bool): Attempt to reconnect if the connection is aborted.
        - **proxies** (dict): Dictionary of proxies, e.g., {'http': 'http://proxy.example.com:8080'}.
        - **ssl_context**: User-defined SSL context.
        - **cert** (str or tuple): Path to SSL client cert file or ('cert', 'key') pair.

        :param kwargs: See description above for all supported arguments

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

        # higher level modules
        self.power_bi = PowerBiService(self._tm1_rest)
        self.loggers = LoggerService(self._tm1_rest)

        self._server = None
        self._monitoring = None

    def logout(self, **kwargs):
        self._tm1_rest.logout(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.logout()
        except Exception as e:
            warnings.warn(f"Logout Failed due to Exception: {e}")

    @property
    def server(self):
        if not self._server:
            self._server = ServerService(self._tm1_rest)
        return self._server

    @property
    def monitoring(self):
        if not self._monitoring:
            self._monitoring = MonitoringService(self._tm1_rest)
        return self._monitoring

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
        with open(file_name, "wb") as file:
            pickle.dump(self, file)

    @classmethod
    def restore_from_file(cls, file_name):
        with open(file_name, "rb") as file:
            return pickle.load(file)

    def re_authenticate(self):
        self._tm1_rest.connect()

    def re_connect(self):
        self._tm1_rest.connect()
