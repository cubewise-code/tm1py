from TM1py.Services import *


class TM1Service:
    """ All features of TM1py are exposed through this service
    
    """

    def __init__(self, **kwargs):
        self._tm1_rest = RESTService(**kwargs)

        # instantiate all Services
        self.annotations = AnnotationService(self._tm1_rest)
        self.chores = ChoreService(self._tm1_rest)
        self.cubes = CubeService(self._tm1_rest)
        self.data = DataService(self._tm1_rest)
        self.dimensions = DimensionService(self._tm1_rest)
        self.elements = ElementService(self._tm1_rest)
        self.hierarchies = HierarchyService(self._tm1_rest)
        self.monitoring = MonitoringService(self._tm1_rest)
        self.processes = ProcessService(self._tm1_rest)
        self.security = SecurityService(self._tm1_rest)
        self.server = ServerService(self._tm1_rest)
        self.subsets = SubsetService(self._tm1_rest)
        self.views = ViewService(self._tm1_rest)

    def logout(self):
        self._tm1_rest.logout()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()
