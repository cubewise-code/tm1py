# -*- coding: utf-8 -*-

from TM1py.Exceptions import TM1pyException


class ObjectService:
    """ Parentclass for all Object Services
    
    """

    ELEMENT_ATTRIBUTES_PREFIX = "}ElementAttributes_"
    SANDBOX_DIMENSION = "Sandboxes"

    BINARY_HTTP_HEADER = {'Content-Type': 'application/octet-stream; odata.streaming=true'}

    def __init__(self, rest_service):
        """ Constructor, Create an instance of ObjectService
        
        :param rest_service: 
        """
        self._rest = rest_service

    def determine_actual_object_name(self, object_class, object_name):
        request = "/api/v1/{}?$filter=tolower(replace(Name, ' ', '')) eq '{}'".format(
            object_class,
            object_name.replace(" ", "").lower().replace("'", "''"))
        response = self._rest.GET(request, odata_escape_single_quotes_in_object_names=False)
        if len(response.json()["value"]) == 0:
            raise ValueError("Object '{}' of type '{}' doesn't exist".format(object_name, object_class))
        return response.json()["value"][0]["Name"]

    def _exists(self, request):
        """ Check if ressource exists in the TM1 Server
        
        :param request: 
        :return: 
        """
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
