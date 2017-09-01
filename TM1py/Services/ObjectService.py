# -*- coding: utf-8 -*-

from TM1py.Exceptions import TM1pyException


class ObjectService:
    """ Parentclass for all Object Services
    
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

    @property
    def version(self):
        return self._rest._version






































