import pickle

from TM1py.Services import *


class TM1Service:
    """ All features of TM1py are exposed through this service
    
    Can be saved and restored from File, to avoid multiple authentication with TM1.
    """
    def __init__(self, **kwargs):
        self._tm1_rest = RESTService(**kwargs)

        # instantiate all Services
        self.chores = ChoreService(self._tm1_rest)
        self.cubes = CubeService(self._tm1_rest)
        self.dimensions = DimensionService(self._tm1_rest)
        self.monitoring = MonitoringService(self._tm1_rest)
        self.processes = ProcessService(self._tm1_rest)
        self.security = SecurityService(self._tm1_rest)
        self.server = ServerService(self._tm1_rest)

        # Deprecated, use cubes.cells instead!
        self.data = CellService(self._tm1_rest)

    def logout(self):
        self._tm1_rest.logout()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    @property
    def version(self):
        return self._tm1_rest.version

    def save_to_file(self, file_name):
        with open(file_name, 'wb') as file:
            pickle.dump(self, file)

    @classmethod
    def restore_from_file(cls, file_name):
        with open(file_name, 'rb') as file:
            return pickle.load(file)
