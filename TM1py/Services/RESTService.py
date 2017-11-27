# -*- coding: utf-8 -*-

import functools
import requests
import sys
from base64 import b64encode
# import Http-Client depending on pyhton version
if sys.version[0] == '2':
    import httplib as http_client
else:
    import http.client as http_client


from TM1py.Exceptions import TM1pyException


def httpmethod(func):
    """ Higher Order Function to wrap the GET, POST, PATCH, PUT, DELETE methods in TM1pyHTTPClient

        Takes care of:
        - encoding of url and payload
        - verfiying response. Throws TM1pyException if StatusCode of Reponse is not OK
    """

    @functools.wraps(func)
    def wrapper(self, request, data=''):
        # Encoding
        request, data = self._url_and_body(request=request, data=data)
        # Do Request
        response = func(self, request, data)
        # Verify
        self.verify_response(response=response)
        return response.text
    return wrapper


class RESTService:
    """ Low level communication with TM1 instance through HTTP.
        Allows to execute HTTP Methods
            - GET
            - POST
            - PATCH
            - DELETE

        Takes Care of 
            - Encodings
            - TM1 User-Login
            - HTTP Headers
            - HTTP Session Management
            - Response Handling

        Based on requests module

    """

    def __init__(self, **kwargs):
        """ Create an instance of RESTService

        :param address: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param base_url - base url e.g. https://localhost:12354/api/v1
        :param user: String - name of the user
        :param password String - password of the user
        :param namespace String - optional CAM namespace
        :param ssl: boolean -  as specified in the tm1s.cfg
        :param loggin: boolean - switch on/off verbose http logging into console
        """
        self._ssl = kwargs['ssl']
        self._address = kwargs['address'] if 'address' in kwargs else None
        self._port = kwargs['port'] if 'port' in kwargs else None
        self._verify = False
        if 'base_url' in kwargs:
            self._base_url = kwargs['base_url']
        else:
            self._base_url = "http{}://{}:{}".format(
                's' if self._ssl else '',
                'localhost' if len(self._address) == 0 else self._address,
                self._port)
        self._version = None
        self._headers = {'Connection': 'keep-alive',
                         'User-Agent': 'TM1py',
                         'Content-Type': 'application/json; odata.streaming=true; charset=utf-8',
                         'Accept': 'application/json;odata.metadata=none,text/plain'}
        # Authorization [Basic, CAM] through Headers
        if 'namespace' in kwargs and kwargs['namespace']:
            token = 'CAMNamespace ' + b64encode(
                str.encode("{}:{}:{}".format(kwargs['user'], kwargs['password'], kwargs['namespace']))).decode("ascii")
        else:
            token = 'Basic ' + b64encode(
                str.encode("{}:{}".format(kwargs['user'], kwargs['password']))).decode("ascii")
        self._headers['Authorization'] = token
        self.disable_http_warnings(self)
        self._s = requests.session()
        self._get_cookies()
        # After we have session cookie drop the Authorization Header
        self._headers.pop('Authorization')
        # Logging
        if 'logging' in kwargs and kwargs['logging']:
            http_client.HTTPConnection.debuglevel = 1

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.logout()

    @httpmethod
    def GET(self, request, data=''):
        """ Perform a GET request against TM1 instance

        :param request: String, for instance : /api/v1/Cubes?$top=1
        :param data: String, empty
        :return: String, the response as text
        """
        return self._s.get(url=request, headers=self._headers, data=data, verify=self._verify)

    @httpmethod
    def POST(self, request, data):
        """ POST request against the TM1 instance

        :param request: String, /api/v1/Cubes
        :param data: String, the payload (json)
        :return:  String, the response as text
        """
        return self._s.post(url=request, headers=self._headers, data=data, verify=self._verify)

    @httpmethod
    def PATCH(self, request, data):
        """ PATCH request against the TM1 instance

        :param request: String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, the payload (json)
        :return: String, the response as text
        """
        return self._s.patch(url=request, headers=self._headers, data=data, verify=self._verify)

    @httpmethod
    def DELETE(self, request, data=''):
        """ Delete request against TM1 instance

        :param request:  String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, empty
        :return: String, the response in text
        """
        return self._s.delete(url=request, headers=self._headers, data=data, verify=self._verify)

    def logout(self):
        """ End TM1 Session and HTTP session

        """
        # Easier to ask for forgiveness than permission
        try:
            # ProductVersion >= TM1 10.2.2 FP 6
            self.POST('/api/v1/ActiveSession/tm1.Close', '')

        except TM1pyException:
            # ProductVersion < TM1 10.2.2 FP 6
            self.POST('/api/logout', '')

    def _get_cookies(self):
        """ perform a simple GET request (Ask for the TM1 Version) to start a session

        """
        url = '{}/api/v1/Configuration/ProductVersion/$value'.format(self._base_url)
        response = self._s.get(url=url, headers=self._headers, data='', verify=self._verify)
        self.verify_response(response)
        self._version = response.text

    def _url_and_body(self, request, data):
        """ create proper url and payload

        """
        url = self._base_url + request
        url = url.replace(' ', '%20').replace('#', '%23')
        data = data.encode('utf-8')
        return url, data

    def is_connected(self):
        """ Check if Connection to TM1 Server is established.

        :Returns:
            Boolean
        """
        try:
            self.GET('/api/v1/Configuration/ServerName/$value', '')
            return True
        except:
            return False

    @property
    def version(self):
        return self._version

    @staticmethod
    def verify_response(response):
        """ check if Status Code is OK

        :Parameters:
            `response`: String
                the response that is returned from a method call

        :Exceptions:
            TM1pyException, raises TM1pyException when Code is not 200, 204 etc.
        """
        if not response.ok:
            raise TM1pyException(response.text, status_code=response.status_code, reason=response.reason)

    @staticmethod
    def disable_http_warnings(self):
        # disable HTTP verification warnings from requests library
        requests.packages.urllib3.disable_warnings()



