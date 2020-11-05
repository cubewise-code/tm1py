import pickle

from TM1py.Services import HierarchyService, SecurityService, ApplicationService, SubsetService, ServerService, \
    MonitoringService, ProcessService, PowerBiService, AnnotationService, ViewService, RestService, CellService, \
    ChoreService, DimensionService, CubeService, ElementService, SandboxService


class TM1Service:
    """ All features of TM1py are exposed through this service
    
    Can be saved and restored from File, to avoid multiple authentication with TM1.
    """

    def __init__(self, **kwargs):
        """
        Initialize the service

        Args:
            self: (todo): write your description
        """
        self._tm1_rest = RestService(**kwargs)

        # instantiate all Services
        self.annotations = AnnotationService(self._tm1_rest)
        self.cells = CellService(self._tm1_rest)
        self.chores = ChoreService(self._tm1_rest)
        self.cubes = CubeService(self._tm1_rest)
        self.dimensions = DimensionService(self._tm1_rest)
        self.elements = ElementService(self._tm1_rest)
        self.hierarchies = HierarchyService(self._tm1_rest)
        self.monitoring = MonitoringService(self._tm1_rest)
        self.power_bi = PowerBiService(self._tm1_rest)
        self.processes = ProcessService(self._tm1_rest)
        self.security = SecurityService(self._tm1_rest)
        self.server = ServerService(self._tm1_rest)
        self.subsets = SubsetService(self._tm1_rest)
        self.applications = ApplicationService(self._tm1_rest)
        self.views = ViewService(self._tm1_rest)

        self.sandboxes = SandboxService(self._tm1_rest)
    def logout(self, **kwargs):
        """
        Logout of the logout.

        Args:
            self: (todo): write your description
        """
        self._tm1_rest.logout(**kwargs)

    def __enter__(self):
        """
        Decor function.

        Args:
            self: (todo): write your description
        """
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Logs the given exception.

        Args:
            self: (todo): write your description
            exception_type: (todo): write your description
            exception_value: (todo): write your description
            traceback: (todo): write your description
        """
        self.logout()

    @property
    def whoami(self):
        """
        Return the current whoami.

        Args:
            self: (todo): write your description
        """
        return self.security.get_current_user()

    @property
    def version(self):
        """
        Access the idle version

        Args:
            self: (todo): write your description
        """
        return self._tm1_rest.version

    @property
    def connection(self):
        """
        Gets the connection.

        Args:
            self: (todo): write your description
        """
        return self._tm1_rest

    def save_to_file(self, file_name):
        """
        Saves the object to a pickle file.

        Args:
            self: (todo): write your description
            file_name: (str): write your description
        """
        with open(file_name, 'wb') as file:
            pickle.dump(self, file)

    @classmethod
    def restore_from_file(cls, file_name):
        """
        Restore a pickle file. pickle file.

        Args:
            cls: (todo): write your description
            file_name: (str): write your description
        """
        with open(file_name, 'rb') as file:
            return pickle.load(file)