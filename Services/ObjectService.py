import json
import collections

from Exceptions.Exceptions import TM1pyException


class ObjectService:
    """
    """
    def __init__(self, rest_service):
        """ Constructor, Create an instance of ObjectService
        
        :param rest_service: 
        """
        self._rest = rest_service

    def exists(self, request):
        try:
            self._rest.GET(request)
            return True
        except TM1pyException as e:
            if e._status_code == 404:
                return False
            raise e







































