import requests
import urllib
import functools
import json

from Exceptions.Exceptions import TM1pyException


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

    def __init__(self, ip, port, login, ssl=True):
        """ Create an instance of RESTService

        :param ip: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param login: instance of TM1pyLogin
        :param ssl: boolean -  as specified in the tm1s.cfg
        """
        self._ip = 'localhost' if ip == '' else ip
        self._port = port
        self._ssl = ssl
        self._version = None
        self._headers = {'Connection': 'keep-alive',
                         'User-Agent': 'TM1py',
                         'Content-Type': 'application/json; odata.streaming=true; charset=utf-8',
                         'Accept': 'application/json,text/plain;odata.metadata=none'}
        # Authorization [Basic, CAM, WIA] through Headers
        if login.auth_type in ['native', 'CAM']:
            self._headers['Authorization'] = login.token
        elif login.auth_type == 'WIA':
            # To be written
            pass
        self.disable_http_warnings(self)
        self._s = requests.session()
        self._get_cookies()
        # logging
        # http_client.HTTPConnection.debuglevel = 1

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
        return self._s.get(url=request, headers=self._headers, data=data, verify=False)

    @httpmethod
    def POST(self, request, data):
        """ POST request against the TM1 instance

        :param request: String, /api/v1/Cubes
        :param data: String, the payload (json)
        :return:  String, the response as text
        """
        return self._s.post(url=request, headers=self._headers, data=data, verify=False)

    @httpmethod
    def PATCH(self, request, data):
        """ PATCH request against the TM1 instance

        :param request: String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, the payload (json)
        :return: String, the response as text
        """
        return self._s.patch(url=request, headers=self._headers, data=data, verify=False)

    @httpmethod
    def DELETE(self, request, data=''):
        """ Delete request against TM1 instance

        :param request:  String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, empty
        :return: String, the response in text
        """
        return self._s.delete(url=request, headers=self._headers, data=data, verify=False)

    def logout(self):
        """ End TM1 Session and HTTP session

        """
        # Easier to ask for forgiveness than permission.
        try:
            # ProductVersion >= TM1 10.2.2 FP 6
            self.POST('/api/v1/ActiveSession/tm1.Close', '')

        except TM1pyException:
            # ProductVersion < TM1 10.2.2 FP 6
            self.POST('/api/logout', '')

    def _get_cookies(self):
        """ perform a simple GET request (Ask for the TM1 Version) to start a session

        """
        url = '{}://{}:{}/api/v1/Configuration/ProductVersion/$value'.format(
            'https' if self._ssl else 'http',
            self._ip,
            self._port)
        response = self._s.get(url=url, headers=self._headers, data='', verify=False)
        self.verify_response(response)
        self._version = response.text

    def _url_and_body(self, request, data):
        """ create proper url and payload

        """
        if self._ssl:
            url = 'https://' + self._ip + ':' + str(self._port) + request
        else:
            url = 'http://' + self._ip + ':' + str(self._port) + request
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



