
'''
TM1py - A python module for TM1
'''

import requests
import logging
import json
import time
import copy
import uuid
import collections
import http.client
from base64 import b64encode


class TM1pyException(Exception):
    ''' The default exception for TM1py

    '''
    def __init__(self, response, status_code, reason):
        self._response = response
        self._status_code = status_code
        self._reason = reason

    def __str__(self):
        return "Text: {} Status Code: {} Reason: {}".format(self._response, self._status_code, self._reason)


class TM1pyLogin:
    ''' Handle Login for different TM1 login types. Instance of this class to be passed to TM1pyHTTPClient, TM1pyQueries


    '''
    def __init__(self, user, password, auth_type, token=None):
        ''' Function is called from static methods

        :param user: String - name user
        :param password: string - pwd
        :param auth_type: string - basic, CAM or WIA
        :param token:
        '''
        self._user = user
        self._password = password
        self._auth_type = auth_type
        self._token = token

    @property
    def auth_type(self):
        return self._auth_type

    @property
    def token(self):
        return self._token

    @classmethod
    def native(cls, user, password):
        ''' Alternate constructor for native login

        :param user:
        :param password:
        :return: instance of TM1pyLogin
        '''
        token = 'Basic ' + b64encode(str.encode("{}:{}".format(user, password))).decode("ascii")
        login = cls(user, password, 'native', token)
        return login

    @classmethod
    def CAM(cls, user, password, CAM_namespace):
        ''' Alternate constructor for CAM login

        :param user:
        :param password:
        :param CAM_namespace:
        :return: instance of TM1pyLogin
        '''
        token = 'CAMNamespace ' + b64encode(str.encode("{}:{}:{}".format(user, password, CAM_namespace))).decode("ascii")
        login = cls(user, password, 'CAM', token)
        return login

    @classmethod
    def WIA_login(cls):
        ''' To be implemented :)

        :return: instance of TM1pyLogin
        '''
        pass

class TM1pyHTTPClient:
    ''' low level communication with TM1 server via http

    '''
    def __init__(self, ip, port, login, ssl=True):
        ''' Create an instance of TM1pyHTTPClient

        :param ip: String - address of the TM1 Server
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param login: instance of TM1pyLogin
        :param ssl: boolean -  as specified in the tm1s.cfg
        '''
        self._ip = 'localhost' if ip == '' else ip
        self._port = port
        self._ssl = ssl
        self._headers= {'Connection': 'keep-alive', 'Cache-Control': 'no-cache', 'User-Agent': 'TM1py',
                       'Content-Type': 'application/json; odata.metadata=minimal; odata.streaming=true; charset=utf-8'}
        # Authorization [Basic, CAM, WIA] through Headers
        if login.auth_type in ['native', 'CAM']:
            self._headers['Authorization'] = login.token
        elif login.auth_type == 'WIA':
            # To be written
            pass
        self._s = requests.session()
        self._get_cookies()
        # disable HTTP verification warnings from requests library
        requests.packages.urllib3.disable_warnings()
        # logging
        # http.client.HTTPConnection.debuglevel = 1

    def GET(self, request, data=''):
        '''Perform a GET request against the TM1 Server.

        :Parameters:
            `request`: String
                the url, for instance : /api/v1/Cubes?$top=1
            `data`: String
               the payload, always an empty String

        :Returns:
            String, the response in text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.get(url=url, headers=self._headers, data=data, verify=False)
        self._varify_response(response=r)
        return r.text

    def POST(self, request, data):
        '''Perform a POST request against the TM1 Server.

        :Parameters:
            `request`: String
                the url, for instance : /api/v1/Cubes
            `data`: String
               the payload (json)

        :Returns:
            String, the response in text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.post(url=url, headers=self._headers, data=data, verify=False)
        self._varify_response(response=r)
        return r.text

    def PATCH(self, request, data):
        '''Perform a PATCH request against the TM1 Server.

        :Parameters:
            `request`: String
                the url, for instance : /api/v1/Dimensions('plan_business_unit')
            `data`: String
               the payload (json)

        :Returns:
            String, the response in text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.patch(url=url, headers=self._headers, data=data, verify=False)
        self._varify_response(response=r)
        return r.text

    def DELETE(self, request, data=''):
        '''Perform a DELETE request against the TM1 Server.

        :Parameters:
            `request`: String
                the url, for instance : /api/v1/Dimensions('plan_business_unit')
            `data`: String
                an empty String

        :Returns:
            String, the response in text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.delete(url=url, headers=self._headers, data=data, verify=False)
        self._varify_response(response=r)
        return r.text

    def _get_cookies(self):
        ''' perform a simple GET request (Ask for the TM1 Version) to start a session

        '''
        if self._ssl:
            url = 'https://' + self._ip + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        else:
            url = 'http://' + self._ip + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        self._s.get(url=url, headers=self._headers, data='', verify=False)

    def _url_and_body(self, request, data):
        ''' create proper url and payload

        '''
        if self._ssl:
            url = 'https://' + self._ip + ':' + str(self._port) + request
        else:
            url = 'http://' + self._ip + ':' + str(self._port) + request
        url = url.replace(' ', '%20').replace('#', '%23')
        #url = requests.utils.quote(url)
        data = data.encode('utf-8')
        return url, data

    def _varify_response(self, response):
        ''' check if Status Code is OK

        :Parameters:
            `response`: String
                the response that is returned from a method call

        :Exceptions:
            TM1pyException, raises TM1pyException when Code is not 200, 204 etc.
        '''
        if not response.ok:
            raise TM1pyException(response.text, status_code=response.status_code, reason=response.reason)


class TM1pyQueries:
    ''' Class offers Queries to interact with a TM1 Server

    - CRUD Features for TM1 objects (Process, Annotation, View, Subset)
        Create method - `create` prefix
        Read methods - `get` prefix
        Update methods - `update prefix`
        Delete methods - `delete prefix`

    - Additional Features
        Retrieve and write data into TM1
        Execute Process or TI Code
        ...
    '''

    def __init__(self, ip, port, login, ssl=True):
        ''' Constructor, Create an instance of TM1Qeueries

        :param ip: String, the IP address of the TM1 Server
        :param port: Int, httpPortNumber as specified in the tm1s.cfg
        :param login: Instance of TM1pyLogin
        :param ssl: Boolean
        '''
        self._ip = ip
        self._port = port
        self._login = login
        self._ssl = ssl
        self._client = TM1pyHTTPClient(ip=ip, port=port, login=login, ssl=ssl)

    @staticmethod
    def get_all_servers_from_adminhost(adminhost='localhost'):
        '''Ask Adminhost for TM1 Servers.

        :Parameters:
            `adminhost`: String
                the IP address of the adminhost

        :Returns:
            List of Servers (instancedsof the TM1py.Server class)
        '''
        conn = http.client.HTTPConnection(adminhost, 5895)
        request = '/api/v1/Servers'
        conn.request('GET', request, body='')
        response = conn.getresponse().read().decode('utf-8')
        response_as_dict = json.loads(response)
        servers = []
        for server_as_dict in response_as_dict['value']:
            server = Server(server_as_dict)
            servers.append(server)
        return servers

    def logout(self):
        ''' End TM1 Session and HTTP session

        '''
        self._client.GET('/api/logout', '')

    def get_server_name(self):
        ''' Ask TM1 Server for its name

        :Returns:
            String, the server name
        '''
        try:
            request = '/api/v1/Configuration/ServerName'
            response = self._client.GET(request, '')
            return json.loads(response)['value']
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_server_name()

    def write_value(self, cube_name, dimension_order, element_tuple, value):
        ''' Write value into cube at specified coordinates

        :Parameters:
            ´cube_name´: String
                name of the target cube
            ´dimension_order´: List/ Tuple
                The dimension names in their correct order
            ´element_tuple´: List/ Tuple
                The coordinates
            ´value´: String/Int/Float
                The value

        '''
        try:
            request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
            body_as_dict = collections.OrderedDict()
            body_as_dict["Cells"] = [{}]
            body_as_dict["Cells"][0]["Tuple@odata.bind"] = \
                ["Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dim, dim, elem)
                 for dim, elem in zip(dimension_order, element_tuple)]
            body_as_dict["Value"] = str(value)
            data = json.dumps(body_as_dict)
            self._client.POST(request=request, data=data)
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.write_value(cube_name, dimension_order, element_tuple, value)

    def write_values(self, cube_name, cellset_as_dict):
        ''' Write values in cube

        :Parameters:
            `cube_name`: String
                name of the cube
            `dimension_order`: List
                cube dimensions in right order
            `cellset_as_dict`: Dictionary
                {(elem_a, elem_b, elem_c): valaue1, (elem_d, elem_e, elem_f) : value2}
        '''
        try:
            dimension_order = self.get_dimension_order(cube_name)
            request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
            updates = ''
            for element_tuple, value in cellset_as_dict.items():
                body_as_dict = collections.OrderedDict()
                body_as_dict["Cells"] = [{}]
                body_as_dict["Cells"][0]["Tuple@odata.bind"] = \
                    ["Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dim, dim, elem)
                     for dim, elem in zip(dimension_order, element_tuple)]
                body_as_dict["Value"] = str(value)
                updates += ',' + json.dumps(body_as_dict)
            updates = '[' + updates[1:] + ']'
            self._client.POST(request=request, data=updates)
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.write_values(cube_name, cellset_as_dict)

    def get_all_cube_names(self):
        '''Ask TM1 Server for list with all cube names

        :Returns:
            List of Strings
        '''
        try:
            response = self._client.GET('/api/v1/Cubes?$select=Name', '')
            cubes = json.loads(response)['value']
            list_cubes = list(entry['Name'] for entry in cubes)
            return list_cubes
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_all_cube_names()

    def get_all_dimension_names(self):
        '''Ask TM1 Server for list with all dimension names

        :Returns:
            List of Strings
        '''
        try:
            response = self._client.GET('/api/v1/Dimensions?$select=Name', '')
            dimensions = json.loads(response)['value']
            list_dimensions = list(entry['Name'] for entry in dimensions)
            return list_dimensions
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_all_dimension_names()

    def execute_process(self, name_process, parameters={}):
        ''' Ask TM1 Server to execute a process

        :Parameters:
            `name_process`: String, name of the process to be executed
            `parameters`: String, for instance {"Parameters": [ { "Name": "pLegalEntity", "Value": "UK01" }] }

        :Returns:
            String, the response
        '''
        try:
            data = json.dumps(parameters)
            return self._client.POST("/api/v1/Processes('" + name_process + "')/tm1.Execute", data=data)
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            return self.execute_process(name_process, parameters)

    def execute_TI_code(self, lines_prolog, lines_epilog):
        ''' Execute lines of code on the TM1 Server

        :param lines_prolog: list - where each element is a valid line of TI code.
        :param lines_epilog: list - where each element is a valid line of TI code.
        '''
        process_name = '}' + 'TM1py' + str(uuid.uuid4())
        p = Process(name=process_name,
                    prolog_procedure=Process.auto_generated_string() + '\r\n'.join(lines_prolog),
                    epilog_procedure=Process.auto_generated_string() + '\r\n'.join(lines_epilog))
        self.create_process(p)
        try:
            self.execute_process(process_name)
        except TM1pyException as e:
            raise e
        finally:
            self.delete_process(process_name)

    def get_last_message_from_messagelog(self, process_name):
        ''' get the latest messagelog entry for a process

        :param process_name: name of the process
        :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        '''
        try:
            request = "/api/v1/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' " \
                      "and contains( Message, '" + process_name + "')"
            response = self._client.GET(request=request)
            message_log_entry = json.loads(response)['value'][0]
            return message_log_entry['Message']
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            return self.get_last_message_from_messagelog(process_name)

    def get_last_message_from_processerrorlog(self, process_name):
        ''' get the latest ProcessErrorLog from a process entity

        :param process_name: name of the process
        :return: String - the errorlog, for instance: "Fehler: Prolog Prozedurzeile (9): Zeichenfolge "US772131" kann nicht in eine reelle Zahl umgewandelt werden."
        '''
        logs_as_list = self.get_processerrorlogs(process_name)
        if len(logs_as_list) == 0:
            return None
        else:
            timestamp = logs_as_list[-1]['Timestamp']
            request = "/api/v1/Processes('{}')/ErrorLogs('{}')/Content".format(process_name, timestamp)
            # response is plain text - due to entity type Edm.Stream
            response = self._client.GET(request=request)
            return response

    def get_processerrorlogs(self, process_name):
        ''' get all ProcessErrorLog entry for a process

        :param process_name: name of the process
        :return: list - Collection of ProcessErrorLogs
        '''
        request = "/api/v1/Processes('{}')/ErrorLogs".format(process_name)
        response = self._client.GET(request=request)
        processerrorlog = json.loads(response)['value']
        return processerrorlog

    # delete process with given process name
    def delete_process(self, name_process):
        ''' Delete Process on TM1 Server

        :Parameters:
            `name_process`: String
                name of the process to be deleted

        :Returns:
            String, the response
        '''
        try:
            request = "/api/v1/Processes('" + name_process + "')"
            response = self._client.DELETE(request, "")
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.delete_process(name_process)

    def is_connected(self):
        ''' Check if Connection to TM1 Server is established.

        :Returns:
            Boolean
        '''
        try:
            response = self._client.GET('/api/v1/Configuration/ServerName', '')
            return True
        except (ConnectionError, ConnectionAbortedError, OSError):
            return False

    def get_all_process_names(self):
        ''' Get List with all process names from TM1 Server

        :Returns:
            List of Strings
        '''
        try:
            response = self._client.GET('/api/v1/Processes?$select=Name', '')
            dict_processes = json.loads(response)['value']
            processes = list(process['Name'] for process in dict_processes)
            return processes
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_all_process_names()

    def get_all_process_names_filtered(self):
        ''' Get List with all process names from TM1 Server.
            Does not return:
                - system process
                - Processes that have Subset as Datasource

        :Returns:
            List of Strings
        '''
        try:
            response = self._client.GET("/api/v1/Processes?$select=Name&$filter=DataSource/Type ne 'TM1DimensionSubset' and  not startswith(Name,'}')", "")
            dict_processes = json.loads(response)['value']
            processes = list(process['Name'] for process in dict_processes)
            return processes
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_all_process_names()


    def get_process(self, name_process):
        ''' Get a process from TM1 Server

        :Parameters:
            `name_process`: String

        :Returns:
             Instance of the TM1py.Process class
        '''

        try:
            request="/api/v1/Processes('" + name_process +"')?$select=*,UIData,VariablesUIData," \
                                                          "DataSource/dataSourceNameForServer," \
                                                          "DataSource/dataSourceNameForClient," \
                                                          "DataSource/asciiDecimalSeparator," \
                                                          "DataSource/asciiDelimiterChar," \
                                                          "DataSource/asciiDelimiterType," \
                                                          "DataSource/asciiHeaderRecords," \
                                                          "DataSource/asciiQuoteCharacter," \
                                                          "DataSource/asciiThousandSeparator," \
                                                          "DataSource/view,"\
                                                          "DataSource/query,"\
                                                          "DataSource/userName,"\
                                                          "DataSource/password,"\
                                                          "DataSource/usesUnicode"
            response = self._client.GET(request, "")
            return Process.from_json(process_as_json=response)
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_process(name_process)

    def update_process(self, process):
        ''' update an existing Process on TM1 Server

        :Parameters:
            `process`: Instance of TM1py.Process class

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Processes('" + process.name + "')"
            response = self._client.PATCH(request, process.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.update_process(process)

    def create_process(self, process):
        ''' post a new process against TM1 Server

        :Parameters:
            `process`: Instance of TM1py.Process class

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Processes"
            response = self._client.POST(request, process.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.create_process(process)

    def create_view(self, view, private=False):
        ''' create a new view on TM1 Server

        :Parameters:
            `view`: instance of subclass of TM1py.View (TM1py.NativeView or TM1py.MDXView)
            `private`: boolean

        :Returns:
            `string` : the response
        '''
        try:
            if private:
                request = "/api/v1/Cubes('" + view._cube + "')/PrivateViews"
            else:
                request = "/api/v1/Cubes('" + view._cube + "')/Views"
            response = self._client.POST(request, view.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.create_view(view)

    def view_exists(self, cube_name, view_name, private=False):
        ''' checks if view exists

        :param cube_name:  string, name of the cube
        :param view_name: string, name of the view
        :param private: boolean

        :return True or False
        '''
        try:
            if private:
                self._client.GET("/api/v1/Cubes('" + cube_name + "')/PrivateViews('" + view_name + "')")
            else:
                self._client.GET("/api/v1/Cubes('" + cube_name + "')/Views('" + view_name + "')")
            return True
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
        except TM1pyException:
            return False

    def get_native_view(self, cube_name, view_name, private=False):
        ''' get a NativeView from TM1 Server

        :param cube_name:  string, name of the cube
        :param view_name:  string, name of the native view
        :param private:    boolean

        :return: instance of TM1py.NativeView
        '''
        try:
            views = "PrivateViews" if private else "Views"
            request = "/api/v1/Cubes('" + cube_name + "')/" + views + "('" + view_name + "')?$expand=" \
                      "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name),  " \
                      "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name), " \
                      "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name), " \
                      "tm1.NativeView/Titles/Selected($select=Name)"
            view_as_json = self._client.GET(request)
            native_view = NativeView.from_json(view_as_json)
            return native_view
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_native_view(self, cube_name, view_name)

    def get_mdx_view(self, cube_name, view_name, private=False):
        ''' get an MDXView from TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the MDX view
        :param private: boolean

        :return: instance of TM1py.MDXView
        '''
        try:
            if private:
                request = "/api/v1/Cubes('{}')/PrivateViews('{}')?$expand=*".format(cube_name, view_name)
            else:
                request = "/api/v1/Cubes('{}')/Views('{}')?$expand=*".format(cube_name, view_name)
            view_as_json = self._client.GET(request)
            mdx_view = MDXView.from_json(view_as_json=view_as_json)
            return mdx_view
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_mdx_view(self, cube_name, view_name)

    def update_view(self, view, private=False):
        ''' update an existing view

        :param view: instance of TM1py.NativeView or TM1py.MDXView
        :return: None
        '''
        if type(view) == MDXView:
            self._update_mdx_view(view, private)
        elif type(view) == NativeView:
            self._update_native_view(view, private)
        else:
            raise TM1pyException('given view is not of type MDXView or NativeView')

    def _update_mdx_view(self, mdx_view, private):
        ''' update an mdx view on TM1 Server

        :param mdx_view: instance of TM1py.MDXView
        :param private: boolean

        :return: string, the response
        '''
        try:
            if private:
                request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(mdx_view.get_cube(), mdx_view.get_name())
            else:
                request = "/api/v1/Cubes('{}')/Views('{}')".format(mdx_view.get_cube(), mdx_view.get_name())
            response = self._client.PATCH(request, mdx_view.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self._update_mdx_view(mdx_view, private=private)

    def _update_native_view(self, native_view, private=False):
        ''' update a native view on TM1 Server

        :param view: instance of TM1py.NativeView
        :param private: boolean

        :return: string, the response
        '''
        try:
            if private:
                request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(native_view.get_cube(), native_view.get_name())
            else:
                request = "/api/v1/Cubes('{}')/Views('{}')".format(native_view.get_cube(), native_view.get_name())
            response = self._client.PATCH(request, native_view.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self._update_native_view(native_view, private)

    def delete_view(self, cube_name, view_name, private=False):
        ''' delete an existing view on the TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: Boolean

        :return: String, the response
        '''
        try:
            if private:
                request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(cube_name, view_name)
            else:
                request = "/api/v1/Cubes('{}')/Views('{}')".format(cube_name, view_name)
            response = self._client.DELETE(request)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.delete_view(cube_name, view_name)

    def get_elements_with_attribute(self, dimension_name, hierarchy_name, attribute_name, attribute_value):
        attribute_name = attribute_name.replace(" ", "")
        if type(attribute_value) is str:
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = Attributes/{} eq '{}';$select=Name)".\
                format(dimension_name, hierarchy_name,attribute_name, attribute_value)
        else:
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = Attributes/{} eq {};$select=Name)"\
                .format(dimension_name, hierarchy_name,attribute_name, attribute_value)
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        return [elem['Name'] for elem in response_as_dict['Elements']]

    def get_dimension_as_dict(self, dimension_name, hierarchy_name):
        dimension_as_json = self._client.GET("/api/v1/Dimensions('" + dimension_name + "')/Hierarchies('" +
                                             hierarchy_name + "')?$expand=Elements($select=Name,Type;$expand="
                                             "Components($select=Name,Type;$expand=Components($select=Name,Type;"
                                             "$expand=Components)))")
        dimension_as_dict = json.loads(dimension_as_json)
        return dimension_as_dict


    # Not complete
    def create_dimension(self, dimension):
        '''
        :notes: UNCOMPLETE!

        :param hierarchy: instance of TM1py.Hierarchy
        :return: None
        '''
        try:
            pass
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.create_dimension(dimension)

    # Not complete
    def delete_dimension(self, dimension_name):
        '''

        :param dimension_name:
        :return:
        '''
        pass

    # Not complete
    def create_hierarchy(self, dimension_name, hierarchy):
        pass

    # Not complete
    def get_hierarchy(self, dimension_name, hierarchy_name):
        pass

    # Not complete
    def update_hierarchy(self, dimension_name, hierarchy_name):
        pass

    # Not complete
    def delete_hierarchy(self, dimension_name, hierarchy_name):
        pass

    def get_all_annotations_from_cube(self, name_cube):
        ''' Get all annotations from given cube as a List.

        :Parameters:
            `name_cube`: name of the cube

        :Returns:
            `List` : list of instances of TM1py.Annotation
        '''
        try:
            request = "/api/v1/Cubes('{}')/Annotations?$expand=DimensionalContext($select=Name)".format(name_cube)
            response = self._client.GET(request, '')
            annotations_as_dict = json.loads(response)['value']
            annotations = [Annotation.from_json(json.dumps(element)) for element in annotations_as_dict]
            return annotations
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_all_annotations_from_cube(name_cube)

    def get_cube_names_and_dimensions(self):
        ''' Get all cubes with its dimensions in a dictionary from TM1 Server

        :Returns:
            `Dictionary` : {cube1 : [dim1, dim2, dim3, ... ], cube2 : ....}
        '''
        try:
            cubes_as_dict = {}
            response = self._client.GET("/api/v1/Cubes?$select=Name&$expand=Dimensions", "")
            resp_as_dict = json.loads(response)['value']
            for entry in resp_as_dict:
                name_cube = entry['Name']
                dimensions = []
                dimensions_as_dict = entry['Dimensions']
                for dimension in dimensions_as_dict:
                    dimensions.append(dimension['Name'])
                cubes_as_dict[name_cube] = dimensions
            return cubes_as_dict
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_cube_names_and_dimensions()

    def _get_view_content_native(self,cube_name, view_name, top=None):
        ''' Get view content as dictionary in its native (cellset-) structure.

        :param cube_name: String
        :param view_name: String
        :param top: Int, number of cells

        :return:
            `Dictionary` : {Cells : {}, 'ID' : '', 'Axes' : [{'Ordinal' : 1, Members: [], ...},
            {'Ordinal' : 2, Members: [], ...}, {'Ordinal' : 3, Members: [], ...} ] }
        '''
        if top is not None:
            request = '/api/v1/Cubes(\'' + cube_name + '\')/Views(\'' + view_name + \
                      '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members($select=UniqueName);$top='\
                      + str(top)+')),Cells($select=Value,Ordinal;$top=' + str(top) + ')'
        else:
            request = '/api/v1/Cubes(\'' + cube_name + '\')/Views(\'' + view_name + \
                      '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members($select=UniqueName))),' \
                      'Cells($select=Value,Ordinal)'

        response = self._client.POST(request, '')
        return json.loads(response)

    def get_view_content(self, cube_name, view_name, top=None):
        ''' Get view content as dictionary with sweet and concise structure

        :param cube_name: String
        :param view_name: String
        :param top: Int, number of cells

        :return:
            Dictionary : {([dim1].[elem1], [dim2][elem6]): 3127.312, ....  }
        '''

        view_as_dict = {}

        response_as_dict = self._get_view_content_native( cube_name, view_name, top)
        dimension_order = self.get_dimension_order(cube_name)

        axe0_as_dict = response_as_dict['Axes'][0]
        axe1_as_dict = response_as_dict['Axes'][1]

        ordinal_cells = 0

        ordinal_axe2 = 0
        # get coordinates on axe 2: Title
        # if there are no elements on axe 2 assign emopty list to elements_on_axe2
        if len(response_as_dict['Axes']) > 2:
            axe2_as_dict = response_as_dict['Axes'][2]
            Tuples_as_dict = axe2_as_dict['Tuples'][ordinal_axe2]['Members']
            elements_on_axe2 = [data['UniqueName'] for data in Tuples_as_dict]
        else:
            elements_on_axe2 = []

        ordinal_axe1 = 0
        for i in range(axe1_as_dict['Cardinality']):
            #get coordinates on axe 1: Rows
            Tuples_as_dict = axe1_as_dict['Tuples'][ordinal_axe1]['Members']
            elements_on_axe1 = [data['UniqueName'] for data in Tuples_as_dict]
            ordinal_axe0 = 0
            for j in range(axe0_as_dict['Cardinality']):
                # get coordinates on axe 0: Columns
                Tuples_as_dict = axe0_as_dict['Tuples'][ordinal_axe0]['Members']
                elements_on_axe0 = [data['UniqueName'] for data in Tuples_as_dict]
                coordinates = elements_on_axe0 + elements_on_axe2 + elements_on_axe1
                coordinates_sorted = self.sort_addresstuple(cube_name, dimension_order, coordinates)
                # get cell value
                value = response_as_dict['Cells'][ordinal_cells]['Value']
                view_as_dict[coordinates_sorted] = value

                ordinal_axe0 += 1
                ordinal_cells += 1
                if top is not None and ordinal_cells >= top:
                    break
            if top is not None and ordinal_cells >= top:
                break
            ordinal_axe1 += 1
        return view_as_dict

    def get_dimension_order(self, name_cube):
        ''' Get the correct order of dimensions in a cube

        :param name_cube: String
        :return:
            List : [dim1, dim2, dim3, etc.]
        '''

        try:
            response = self._client.GET('/api/v1/Cubes(\'' + name_cube + '\')/Dimensions?$select=Name', '')
            response_as_dict = json.loads(response)['value']
            dimension_order = [element['Name'] for element in response_as_dict]
            return dimension_order
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_dimension_order(name_cube)

    def sort_addresstuple(self, dimension_order, unsorted_addresstuple):
        ''' Sort the given mixed up addresstuple

        :param cube_name: String
        :param dimension_order: list of dimension names in correct order
        :param unsorted_addresstuple: list of Strings - ['[dim2].[elem4]','[dim1].[elem2]',...]

        :return:
            Tuple: ('[dim1].[elem2]','[dim2].[elem4]',...)
        '''
        sorted_addresstupple = []
        for dimension in dimension_order:
            address_element = [item for item in unsorted_addresstuple if item.startswith('[' + dimension + '].')]
            sorted_addresstupple.append(address_element[0])
        return tuple(sorted_addresstupple)


    def create_annotation(self, annotation):
        ''' create an Annotation

            :param annotation: instance of TM1py.Annotation

            :return
                string: the response
        '''
        try:
            request = "/api/v1/Annotations"

            payload = collections.OrderedDict()
            payload["Text"] = annotation._text
            payload["ApplicationContext"] = [{"Facet@odata.bind": "ApplicationContextFacets('}Cubes')",
                                              "Value": annotation._object_name}]
            payload["DimensionalContext@odata.bind"] = []
            for dimension, element in zip(self.get_dimension_order(annotation._object_name), annotation._dimensional_context):
                payload["DimensionalContext@odata.bind"].append("Dimensions('" + dimension + "')/Hierarchies('"
                                                                + dimension + "')/Members('" + element + "')")
            payload['objectName'] = annotation._object_name
            payload['commentValue'] = annotation._comment_value
            payload['commentType'] = 'ANNOTATION'
            payload['commentLocation'] =  ','.join(annotation._dimensional_context)
            response = self._client.POST(request, json.dumps(payload, ensure_ascii=False, sort_keys=False))
            return response
        except(ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.create_Annotation(annotation)

    def get_annotation(self, id):
        ''' get an annotation from any cube from TM1 Server

            :param id: String, the id of the annotation

            :return:
                Annotation: an instance of the TM1py.Annoation
        '''
        try:
            request = "/api/v1/Annotations('{}')?$expand=DimensionalContext($select=Name)".format(id)
            annotation_as_json = self._client.GET(request=request)
            return Annotation.from_json(annotation_as_json)
        except(ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_annotation(id)


    def update_annotation(self, annotation):
        ''' update Annotation on TM1 Server

            :param annotation: instance of TM1py.Annotation

            :Notes:
                updateable attributes:
                    commentValue
        '''
        try:
            request = "/api/v1/Annotations('{}')".format(annotation._id)
            return self._client.PATCH(request=request, data=annotation.body)
        except(ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.update_annotation(annotation)

    def delete_annotation(self, id):
        ''' delete Annotation on TM1 Server

            :param id: string, the id of the annotation

            :return:
                string: the response
        '''
        try:
            request = "/api/v1/Annotations('{}')".format(id)
            return self._client.DELETE(request=request)
        except(ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.delete_annotation(id)


    def create_subset(self, subset):
        ''' create subset on the TM1 Server

            :param subset: TM1py.Subset, the subset that shall be created

            :return:
                string: the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + subset._dimension_name +  '\')/Hierarchies(\'' + subset._dimension_name\
                      + '\')/Subsets'
            response = self._client.POST(request, subset.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.create_subset(subset)

    def get_subset(self, dimension_name, subset_name):
        ''' get a subset from the TM1 Server

            :param dimension_name: string, name of the dimension
            :param subset_name: string, name of the subset

            :return:
                subset: instance of the Subset class
        '''
        try:
            request = '/api/v1/Dimensions(\'' + dimension_name + '\')/Hierarchies(\'' + dimension_name + \
                      '\')/Subsets(\'' + subset_name + '\')?$expand=Hierarchy($select=Dimension),Elements($select=Name)'
            response = self._client.GET(request=request)
            return Subset.from_json(response)
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.get_subset(dimension_name, subset_name)

    def update_subset(self, subset):
        ''' update a subset on the TM1 Server
            :Parameters:
                `subset` : Subset
                    the new subset

            :return:
                string: the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + subset._dimension_name +  '\')/Hierarchies(\'' + subset._dimension_name\
                      + '\')/Subsets(\'' + subset._subset_name + '\')'
            response = self._client.PATCH(request=request, data=subset.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.update_subset(subset)

    def delete_subset(self, dimension_name, subset_name):
        ''' delete a subset on the TM1 Server
            :Parameters:
                `name_dimension` : String, name of the dimension
                `name_subset` : String, name of the subset

            :Returns:
                `string` : the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + dimension_name +  '\')/Hierarchies(\'' + dimension_name\
                      + '\')/Subsets(\'' + subset_name + '\')'
            response = self._client.DELETE(request=request,data='')
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)
            self.delete_subset(dimension_name, subset_name)

class Server:
    ''' Abstraction of the TM1 Server

        :Notes:
            contains the information you get from http://localhost:5895/api/v1/Servers
            no methods so far
    '''
    def __init__(self, server_as_dict):
        self.name = server_as_dict['Name']
        self.ip_address = server_as_dict['IPAddress']
        self.ip_v6_address = server_as_dict['IPv6Address']
        self.port_number = server_as_dict['PortNumber']
        self.client_message_port_number = server_as_dict['ClientMessagePortNumber']
        self.http_port_number = server_as_dict['HTTPPortNumber']
        self.using_ssl = server_as_dict['UsingSSL']
        self.accepting_clients = server_as_dict['AcceptingClients']

class Subset:
    ''' Abstraction of the TM1 Subset

        :Notes:
            Done and tested. unittests available.

            subset-type
                class handles subset type implicitly. According to this logic:
                    self._elements is not None -> static
                    self._expression is not None -> dyamic
                    self._expression is not None and self._elements is not None -> dynamic
    '''
    def __init__(self, dimension_name, subset_name, expression=None, elements=None):
        '''

        :param dimension_name: String
        :param subset_name: String
        :param expression: String
        :param elements: List, element names
        '''
        self._dimension_name = dimension_name
        self._subset_name = subset_name
        self._expression = expression
        self._elements = elements

    @classmethod
    def from_json(cls, subset_as_json):
        ''' Alternative constructor
                :Parameters:
                    `subset_as_json` : string, JSON
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        '''

        subset_as_dict = json.loads(subset_as_json)
        return cls.from_dict(subset_as_dict=subset_as_dict)

    @classmethod
    def from_dict(cls, subset_as_dict):
        return cls(dimension_name=subset_as_dict["UniqueName"][1:subset_as_dict["UniqueName"].find('].[')],
                   subset_name=subset_as_dict['Name'],
                   expression=subset_as_dict['Expression'],
                   elements=[element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else None)

    @property
    def body(self):
        ''' same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        '''
        if self._expression:
            return self._construct_body_dynamic()
        else:
            return self._construct_body_static()

    def get_name(self):
        return self._subset_name

    def get_dimension_name(self):
        return self._dimension_name

    def set_subset_name(self, subset_name):
        ''' set the subset name
                :Parameters:
                    `dimension_name` : string
                        the name of the subset
        '''
        self._subset_name = subset_name

    def set_dimension_name(self, dimension_name):
        ''' set the dimension in which the subset shall be created
                :Parameters:
                    `dimension_name` : string
                        name of the dimension
        '''
        self._dimension_name = dimension_name

    def set_expression(self, expression):
        ''' set Expression for subset
                :Parameters:
                    `expression` : string
                        a valid TM1 - MDX expression

                :Notes:
                    when called on a static subset, makes subset turn into dynamic.
        '''
        self._expression = expression

    def add_elements(self, elements):
        ''' add Elements to static subsets
            :Parameters:
                `elements` : list of element names
        '''
        self._elements = self._elements + elements

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        body_as_dict['Hierarchy@odata.bind'] = "Dimensions('" + self._dimension_name + \
                                               "')/Hierarchies('" + self._dimension_name + "')"
        body_as_dict['Expression'] = self._expression
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        body_as_dict['Hierarchy@odata.bind'] = "Dimensions('" + self._dimension_name + \
                                               "')/Hierarchies('" + self._dimension_name + "')"
        elements_in_list = []
        for element in self._elements:
            elements_in_list.append('Dimensions(\'' + self._dimension_name + '\')/Hierarchies(\'' +
                                    self._dimension_name + '\')/Elements(\'' + element + '\')')
            body_as_dict['Elements@odata.bind'] = elements_in_list
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class AnnonymousSubset(Subset):
    ''' Abstraction of unregistered Subsets used in NativeViews (Check TM1py.ViewAxisSelection)

    '''
    def __init__(self, dimension_name, expression=None, elements=None):
        Subset.__init__(self, dimension_name=dimension_name, subset_name='', expression=expression, elements=elements)

    @classmethod
    def from_json(cls, subset_as_json):
        ''' Alternative constructor
                :Parameters:
                    `subset_as_json` : string, JSON
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        '''
        subset_as_dict = json.loads(subset_as_json)
        return cls.from_dict(subset_as_dict=subset_as_dict)

    @classmethod
    def from_dict(cls, subset_as_dict):
        ''' Alternative constructor
                :Parameters:
                    `subset_as_dict` : dictionary
                        representation of Subset as specified in CSDL

                :Returns:
                    `Subset` : an instance of this class
        '''
        return cls(dimension_name = subset_as_dict["Hierarchy"]['Dimension']['Name'],
                   expression = subset_as_dict['Expression'],
                   elements = [element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else None)

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict["Hierarchy@odata.bind"] = "Dimensions('" + self._dimension_name + \
                                               "')/Hierarchies('" + self._dimension_name + "')"
        body_as_dict['Expression'] = self._expression
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict["Hierarchy@odata.bind"] = "Dimensions('" + self._dimension_name + \
                                               "')/Hierarchies('" + self._dimension_name + "')"
        elements_in_list = []
        for element in self._elements:
            elements_in_list.append('Dimensions(\'' + self._dimension_name + '\')/Hierarchies(\'' +
                                    self._dimension_name + '\')/Elements(\'' + element + '\')')
            body_as_dict['Elements@odata.bind'] = elements_in_list
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)


class View:
    ''' Abstraction of TM1 View
        serves as a parentclass for TM1py.MDXView and TM1py.NativeView

    '''
    def __init__(self, cube, name):
        self._cube = cube
        self._name = name

    def get_cube(self):
        return self._cube

    def get_name(self):
        return self._name

class MDXView(View):
    ''' Abstraction on TM1 MDX view

        :usecase:
            user defines view with this class and creates it on TM1 Server.
            user calls get_view_data_structured from TM1pyQueries function to retrieve data from View

        :Notes:
            Complete, functional and tested
    '''
    def __init__(self, cube_name, view_name, MDX):
        View.__init__(self, cube_name, view_name)
        self._MDX = MDX

    @property
    def body(self):
        return self.construct_body()

    @classmethod
    def from_json(cls, view_as_json):
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict)

    @classmethod
    def from_dict(cls, view_as_dict):
        return cls(cube_name=view_as_dict['Cube']['Name'], view_name=view_as_dict['Name'],MDX=view_as_dict['MDX'])

    def set_MDX(self, MDX):
        self._MDX = MDX

    def construct_body(self):
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._MDX
        return json.dumps(mdx_view_as_dict, ensure_ascii=False, sort_keys=False)

class NativeView(View):
    ''' Abstraction of TM1 Nativeview

        :usecase:
            user defines view with this class and creates it on TM1 Server.
            user calls get_view_content method from TM1pyQueries to retrieve data from View

        :Notes:
            Complete, functional and tested
    '''
    def __init__(self, name_cube, name_view, suppress_empty_columns=False, suppress_empty_rows=False,
                 format_string="0.#########\fG|0|", titles = [], columns = [], rows = []):
        View.__init__(self, name_cube, name_view)
        self._suppress_empty_columns = suppress_empty_columns
        self._suppress_empty_rows = suppress_empty_rows
        self._format_string = format_string
        self._titles = titles
        self._columns = columns
        self._rows = rows


    @classmethod
    def from_json(cls, view_as_json):
        ''' Alternative constructor
                :Parameters:
                    `view_as_json` : string, JSON

                :Returns:
                    `View` : an instance of this class
        '''
        view_as_dict = json.loads(view_as_json)
        titles, columns, rows = [], [], []

        for selection in view_as_dict['Titles']:
            if selection['Subset']['Name'] == '':
                subset = AnnonymousSubset.from_dict(selection['Subset'])
            else:
                subset = Subset.from_dict(selection['Subset'])
            selected = selection['Selected']['Name']
            titles.append(ViewTitleSelection(dimension_name=subset.get_dimension_name(),
                                             subset=subset, selected=selected))
        for i, axe in enumerate([view_as_dict['Columns'], view_as_dict['Rows']]):
            for selection in axe:
                if selection['Subset']['Name'] == '':
                    subset = AnnonymousSubset.from_dict(selection['Subset'])
                else:
                    subset = Subset.from_dict(selection['Subset'])
                axis_selection = ViewAxisSelection(dimension_name=subset.get_dimension_name(),
                                                   subset=subset)
                columns.append(axis_selection) if i == 0 else rows.append(axis_selection)

        return cls(name_cube = view_as_dict["@odata.context"][20:view_as_dict["@odata.context"].find("')/")],
                   name_view = view_as_dict['Name'],
                   suppress_empty_columns = view_as_dict['SuppressEmptyColumns'],
                   suppress_empty_rows = view_as_dict['SuppressEmptyRows'],
                   format_string = view_as_dict['FormatString'],
                   titles = titles,
                   columns = columns,
                   rows = rows)

    @property
    def body(self):
        return self._construct_body()

    @property
    def as_MDX(self):
        # create the MDX Query
        mdx = "SELECT "

        # Iterate through axes - append ON COLUMNS, ON ROWS statement
        # 4 Options
        # 1. No elements on rows - no elements on columns -> exception
        # 2. No elements on rows - elements on columns
        # 3. Elements on rows - no elements on columns -> exception
        # 4. Elements on rows - elements on columns
        for i, axe in enumerate((self._rows, self._columns)):
            for j, axis_selection in enumerate(axe):
                subset = axis_selection._subset
                if subset._expression is not None:
                    mdx += subset._expression
                else:
                    elements_as_unique_names = ['[' + axis_selection._dimension_name + '].[' + elem + ']' for elem in
                                                subset._elements]
                    mdx_subset = '{' + ','.join(elements_as_unique_names) + '}'
                    if j == 0:
                        mdx += mdx_subset
                    else:
                        mdx += '*' + mdx_subset
            if i == 0:
                if len(self._rows) > 0:
                    mdx += 'on {}, '.format('ROWS')
            else:
                mdx += 'on {} '.format('COLUMNS')

        # append the FROM statement
        mdx += 'FROM [' + self._cube + '] '

        # itarate through titles - append the WHERE statement
        if len(self._titles) > 0:
            unique_names = []
            for title_selection in self._titles:
                dimension_name = title_selection._dimension_name
                selection = title_selection._selected
                unique_names.append('[' + dimension_name + '].[' + selection + ']')
            mdx += 'WHERE (' + ','.join(unique_names) + ') '

        return mdx

    def set_suppress_empty_cells(self, value):
        self.set_suppress_empty_columns(value)
        self.set_suppress_empty_rows(value)

    def set_suppress_empty_columns(self, value):
        self._suppress_empty_columns = value

    def set_suppress_empty_rows(self, value):
        self._suppress_empty_rows = value

    def set_format_string(self, new_format):
        self._format_string = new_format

    def add_column(self, dimension_name, subset=None):
        ''' Add Dimension or Subset to the column-axis

        :param dimension_name: name of the dimension
        :param subset: instance of TM1py.Subset. Can be None instead.
        :return:
        '''
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._columns.append(view_axis_selection)

    def remove_column(self, dimension_name):
        ''' remove dimension from the column axis

        :param dimension_name:
        :return:
        '''
        for column in self._columns:
            if column._dimension_name == dimension_name:
                self._columns.remove(column)

    def add_row(self, dimension_name, subset=None):
        ''' Add Dimension or Subset to the row-axis

        :param dimension_name:
        :param subset: instance of TM1py.Subset. Can be None instead.
        :return:
        '''
        view_axis_selection = ViewAxisSelection(dimension_name=dimension_name, subset=subset)
        self._rows.append(view_axis_selection)

    def remove_row(self, dimension_name):
        ''' remove dimension from the row axis

        :param dimension_name:
        :return:
        '''
        for row in self._rows:
            if row._dimension_name == dimension_name:
                self._rows.remove(row)

    def add_title(self, dimension_name, selection, subset=None):
        ''' Add subset and element to the titles-axis

        :param dimension_name: name of the dimension.
        :param selection: name of an element.
        :param subset:  instance of TM1py.Subset. Can be None instead.
        :return:
        '''
        view_title_selection = ViewTitleSelection(dimension_name, subset, selection)
        self._titles.append(view_title_selection)

    def remove_title(self, dimension_name):
        ''' remove dimension from the titles-axis

        :param dimension_name: name of the dimension.
        :return:
        '''
        for title in self._titles:
            if title._dimension_name == dimension_name:
                self._titles.remove(title)

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the NativeView entity.

        :return: string, the valid JSON
        '''
        top_json = "{\"@odata.type\": \"ibm.tm1.api.v1.NativeView\",\"Name\": \"" + self._name +"\","
        columns_json = ','.join([column.body for column in self._columns])
        rows_json = ','.join([row.body for row in self._rows])
        titles_json = ','.join([title.body for title in self._titles])
        bottom_json = "\"SuppressEmptyColumns\": " + str(self._suppress_empty_columns).lower() + \
                      ",\"SuppressEmptyRows\":" + str(self._suppress_empty_rows).lower() + \
                      ",\"FormatString\": \"" + self._format_string + "\"}"
        return top_json + '\"Columns\":[' + columns_json + '],\"Rows\":[' + rows_json + \
                    '],\"Titles\":[' + titles_json + '],' + bottom_json

class ViewAxisSelection:
    ''' Describing what is selected in a dimension on an axis. Can be a registered Subset or an annonymous ubset

    '''
    def __init__(self, dimension_name, subset):
        '''
            :Parameters:
                `dimension_name` : String
                `subset` : Subset or AnnonymousSubset
        '''
        self._subset = subset
        self._dimension_name = dimension_name

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the ViewAxisSelection entity.

        :return: string, the valid JSON
        '''
        if type(self._subset) is Subset:
            return "{\"Subset@odata.bind\": \"Dimensions('" + self._dimension_name + "')/Hierarchies('" \
                + self._dimension_name + "')/Subsets('" + self._subset.get_name() + "')\"}"
        elif type(self._subset) is AnnonymousSubset:
            s = self._subset.body
            return '{\"Subset\":' + s + '}'

class ViewTitleSelection:
    ''' Describing what is selected in a dimension on the title. Can be a registered Subset or an Annonymous subset

    '''
    def __init__(self, dimension_name, subset, selected):
        self._dimension_name = dimension_name
        self._subset = subset
        self._selected = selected

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the ViewTitleSelection entity.

        :return: string, the valid JSON
        '''
        if type(self._subset) is Subset:
            s_subset = "\"Subset@odata.bind\": \"Dimensions('" + self._dimension_name + "')/Hierarchies('" \
                 + self._dimension_name + "')/Subsets('" + self._subset.get_name() + "')\""
            return "{" + s_subset + ", \"Selected@odata.bind\": \"" +" Dimensions('" + self._dimension_name + \
                   "')/Hierarchies('" + self._dimension_name + "')/Elements('" + self._selected + "')\"}"
        elif type(self._subset) is AnnonymousSubset:
            s_subset = self._subset.body
            return "{ \"Subset\" : " + s_subset + ", \"Selected@odata.bind\": \"" +" Dimensions('" + \
                   self._dimension_name + "')/Hierarchies('" + self._dimension_name + "')/Elements('" + \
                   self._selected + "')\"}"

# uncomplete
class Dimension:
    ''' Abstraction of TM1 Dimension.

        :Notes:
            Not complete. Not tested.
            A Dimension is a container for hierarchies.
    '''
    def __init__(self, name):
        '''
        :Parameters:
            - `name` : string
                the name of the dimension
        '''
        self._name = name
        self._hierarchies = []

    @property
    def body(self):
        return self._construct_body()

    @property
    def unique_name(self):
            return '[' + self._name + ']'

    def set_name(self, name):
        self._name = name

    def add_hierarchy(self, hierarchy):
        self._hierarchies.append(hierarchy)

    def _construct_body(self):
        self.body_as_dict = collections.OrderedDict()
        self.body_as_dict["@odata.type"] = "ibm.tm1.api.v1.Dimension"
        self.body_as_dict["Name"] = self._name
        return json.dumps(self.body_as_dict, ensure_ascii=False, sort_keys=False)

# uncomplete
class Hierarchy:
    '''

        :Notes:
            Not complete. Not tested.
    '''

    def __init__(self, name_hierarchy, name_dimension, elements=[], element_attributes=[], edges=[]):
        self._name = name_hierarchy
        self._elements = elements
        self._element_attributes = element_attributes
        self._edges = edges

    @property
    def body(self):
        return self._construct_body()

    def add_element(self, name_element, type_element):
        if name_element in [elem['Name'] for elem in self._elements]:
            # elementname already used
            raise TM1pyException("Elementname has to be unqiue")
        self._elements.append({'Name': name_element, 'Type': type_element})

    def add_edge(self, name_parent_element, name_component_element):
        self._edges.add({'ParentName': name_parent_element, 'ComponentName': name_component_element})

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name']=self._name
        body_as_dict['Elements']=[]
        for i, element in enumerate(self._elements):
            body_as_dict['Elements'].append(element.body)

# uncomplete
class Element:
    def __init__(self, element_name, element_type, element_attributes= None):
        self._element_name = element_name
        self._element_type = element_type
        self._element_attributes = element_attributes


    def body(self):
        return self._construct_body()

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._element_name
        body_as_dict['Type'] = self._element_type
        return body_as_dict

# uncomplete
class Edge:
    def __init__(self, parent_name, component_name, weight):
        self._parent_name = parent_name
        self._component_name = component_name
        self._weight = weight



class Annotation:
    ''' abtraction of TM1 Annotation

        :Notes:
            - Class complete, functional and tested for text annotations !
            - doesnt cover Attachments though
    '''
    def __init__(self, comment_value, object_name, dimensional_context, comment_type = 'ANNOTATION', id=None, text='',
                 creator=None, created=None, last_updated_by=None, last_updated=None):
        self._id = id
        self._text = text
        self._creator = creator
        self._created = created
        self._last_updated_by = last_updated_by
        self._last_updated = last_updated
        self._dimensional_context = dimensional_context
        self._comment_type = comment_type
        self._comment_value = comment_value
        self._object_name = object_name

    @classmethod
    def from_json(cls, annotation_as_json):
        ''' Alternative constructor

        :param annotation_as_json: String, JSON
        :return: instance of TM1py.Process
        '''
        annotation_as_dict = json.loads(annotation_as_json)
        id = annotation_as_dict['ID']
        text = annotation_as_dict['Text']
        creator = annotation_as_dict['Creator']
        created = annotation_as_dict['Created']
        last_updated_by = annotation_as_dict['LastUpdatedBy']
        last_updated = annotation_as_dict['LastUpdated']
        dimensional_context = [item['Name'] for item in annotation_as_dict['DimensionalContext']]
        comment_type = annotation_as_dict['commentType']
        comment_value = annotation_as_dict['commentValue']
        object_name = annotation_as_dict['objectName']
        return cls(comment_value=comment_value, object_name=object_name, dimensional_context=dimensional_context,
                   comment_type=comment_type, id=id, text=text, creator=creator, created=created,
                   last_updated_by=last_updated_by, last_updated=last_updated)

    @property
    def body(self):
        return self._construct_body()

    def get_comment_value(self):
        return self._comment_value

    def get_id(self):
        return self._id

    def set_comment_value(self, comment_value):
        self._comment_value = comment_value

    def move(self, dimension_order, dimension, source_element, target_element):
        ''' move annotation on given dimension from source_element to target_element
            :Parameters:
                `dimension_order` : List
                    order of the dimensions in the cube
                `dimension` : String
                    name of the dimension
                `source_element` : String
                    name of the source element
                `target_element` : String
                    name of the target_element
        '''
        for i, dimension_iter in enumerate(dimension_order):
            if dimension_iter.lower() == dimension.lower():
                if self._dimensional_context[i] == source_element:
                    self._dimensional_context[i] = target_element

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the Annotation entity.

        :return: string, the valid JSON
        '''
        dimensional_context = [{'Name': element} for element in self._dimensional_context]
        body = collections.OrderedDict()
        body['ID'] = self._id
        body['Text'] = self._text
        body['Creator'] = self._creator
        body['Created'] = self._created
        body['LastUpdatedBy'] = self._last_updated_by
        body['LastUpdated'] = self._last_updated
        body['DimensionalContext'] = dimensional_context
        commentLocations = ''
        for element in self._dimensional_context:
            commentLocations = commentLocations + ',' + element
        body['commentLocation'] = commentLocations[1:]
        body['commentType'] = self._comment_type
        body['commentValue'] = self._comment_value
        body['objectName'] = self._object_name
        return json.dumps(body, ensure_ascii=False, sort_keys=False)

class Process:
    ''' abstraction of a TM1 Process.

        :Notes:
        - class complete, functional and tested !!
        - issues with password for processes with for ODBC Datasource
    '''

    def __init__(self, name, has_security_access=False, ui_data="CubeAction=1511€DataAction=1503€CubeLogChanges=0€",
                 parameters=[], variables=[], variables_ui_data=[], prolog_procedure='', metadata_procedure='',
                 data_procedure='', epilog_procedure= '', datasource_type='None', datasource_ascii_decimal_separator='.',
                 datasource_ascii_delimiter_char=';', datasource_ascii_delimiter_type='Character',
                 datasource_ascii_header_records=1, datasource_ascii_quote_character='', datasource_ascii_thousand_separator=',',
                 datasource_data_source_name_for_client='', datasource_data_source_name_for_server='', datasource_password='',
                 datasource_user_name='', datasource_query='', datasource_uses_unicode=True, datasource_view=''):
        ''' Default construcor

        :param name: name of the process - mandatory
        :param others: all other parameters optional
        :return:
        '''
        self.counter_variables = 0
        self.counter_parameters = 0
        self.name = name
        self.has_security_access = has_security_access
        self.ui_data = ui_data
        self.parameters = []
        for item in parameters:
            self.parameters.append(item)
            self.counter_parameters += 1
        self.variables, self.variables_ui_data = [], []
        for variable, ui_data in zip(variables, variables_ui_data):
            self.variables.append(variable)
            self.variables_ui_data.append(ui_data)
            self.counter_variables += 1
        self.prolog_procedure = self.auto_generated_string() + prolog_procedure \
            if "#****Begin: Generated Statements***" not in prolog_procedure else prolog_procedure
        self.metadata_procedure =self.auto_generated_string() + metadata_procedure \
            if "#****Begin: Generated Statements***" not in metadata_procedure else metadata_procedure
        self.data_procedure = self.auto_generated_string() +  data_procedure \
            if "#****Begin: Generated Statements***" not in data_procedure else data_procedure
        self.epilog_procedure = self.auto_generated_string() + epilog_procedure \
            if "#****Begin: Generated Statements***" not in epilog_procedure else epilog_procedure
        self.datasource_type = datasource_type
        self.datasource_ascii_decimal_separator = datasource_ascii_decimal_separator
        self.datasource_ascii_delimiter_char = datasource_ascii_delimiter_char
        self.datasource_ascii_delimiter_type = datasource_ascii_delimiter_type
        self.datasource_ascii_header_records = datasource_ascii_header_records
        self.datasource_ascii_quote_character = datasource_ascii_quote_character
        self.datasource_ascii_thousand_separator = datasource_ascii_thousand_separator
        self.datasource_data_source_name_for_client = datasource_data_source_name_for_client
        self.datasource_data_source_name_for_server = datasource_data_source_name_for_server
        self.datasource_password = datasource_password
        self.datasource_user_name = datasource_user_name
        self.datasource_query = datasource_query
        self.datasource_uses_unicode = datasource_uses_unicode
        self.datasource_view = datasource_view

    @classmethod
    def from_json(cls, process_as_json):
        ''' Alternative constructor
                :Parameters:
                    `process_as_json` : string, JSON
                        response of /api/v1/Processes('x')?$expand=*

                :Returns:
                    `Process` : an instance of this class
        '''
        process_as_dict = json.loads(process_as_json)
        return cls.from_dict(process_as_dict)

    @classmethod
    def from_dict(cls, process_as_dict):
        ''' Alternative constructor
                :Parameters:
                    `process_as_dict` : Dictionary
                        process as a dictionary

                :Returns:
                    `Process` : an instance of this class
        '''
        f = lambda dict, key : dict[key] if key in dict else ''
        return cls(name=process_as_dict['Name'],
                   has_security_access=process_as_dict['HasSecurityAccess'],
                   ui_data=process_as_dict['UIData'],
                   parameters=process_as_dict['Parameters'],
                   variables=process_as_dict['Variables'],
                   variables_ui_data = process_as_dict['VariablesUIData'],
                   prolog_procedure=process_as_dict['PrologProcedure'],
                   metadata_procedure=process_as_dict['MetadataProcedure'],
                   data_procedure=process_as_dict['DataProcedure'],
                   epilog_procedure=process_as_dict['EpilogProcedure'],
                   datasource_type=f(process_as_dict['DataSource'], 'Type'),
                   datasource_ascii_decimal_separator=f(process_as_dict['DataSource'], 'asciiDecimalSeparator'),
                   datasource_ascii_delimiter_char=f(process_as_dict['DataSource'], 'asciiDelimiterChar'),
                   datasource_ascii_delimiter_type=f(process_as_dict['DataSource'], 'asciiDelimiterType'),
                   datasource_ascii_header_records=f(process_as_dict['DataSource'], 'asciiHeaderRecords'),
                   datasource_ascii_quote_character=f(process_as_dict['DataSource'], 'asciiQuoteCharacter'),
                   datasource_ascii_thousand_separator=f(process_as_dict['DataSource'], 'asciiThousandSeparator'),
                   datasource_data_source_name_for_client=f(process_as_dict['DataSource'], 'dataSourceNameForClient'),
                   datasource_data_source_name_for_server=f(process_as_dict['DataSource'], 'dataSourceNameForServer'),
                   datasource_password=f(process_as_dict['DataSource'], 'password'),
                   datasource_user_name=f(process_as_dict['DataSource'], 'userName'),
                   datasource_query=f(process_as_dict['DataSource'], 'query'),
                   datasource_uses_unicode=f(process_as_dict['DataSource'], 'usesUnicode'),
                   datasource_view=f(process_as_dict['DataSource'], 'view'))

    @staticmethod
    def auto_generated_string():
        ''' the auto_generated_string code is required to be in all code-tabs.

        :return: string
        '''
        return "\r\n#****Begin: Generated Statements***\r\n#****End: Generated Statements****\r\n\r\n\r\n"

    @property
    def body(self):
        return self.construct_body()

    def add_variable(self, name_variable, type):
        ''' add variable to the process

        :param name_variable: -
        :param type: String or Numeric
        :return:
        '''
        # variable consists of actual variable and UI-Information ('ignore','other', etc.)
        # 1. handle Variable info
        variable = {'Name': name_variable,
                    'Type': type,
                    'Position': len(self.variables) + 1,
                    'StartByte': 0,
                    'EndByte': 0}
        self.variables.append(variable)
        # 2. handle UI info
        var_type = 33 if type == 'Numeric' else 32
        # '' !
        variable_ui_data = 'VarType=' +  str(var_type) + '' + 'ColType=' + str(827)+ ''
        '''
        mapping VariableUIData:
            VarType 33 -> Numeric
            VarType 32 -> String
            ColType 827 -> Other
        '''
        self.variables_ui_data.append(variable_ui_data)

    def add_parameter(self, name, prompt, value):
        parameter = {'Name': name,
                     'Prompt': prompt,
                     'Value': value}
        self.parameters.append(parameter)

    def set_name(self, name):
        self.name = name

    def set_has_security_access(self, has_security_access):
        self.has_security_access = has_security_access

    def set_prolog_procedure(self, prolog_procedure):
        self.prolog_procedure = self.auto_generated_string() + prolog_procedure \
            if "#****Begin: Generated Statements***" not in prolog_procedure else prolog_procedure

    def set_metadata_procedure(self, metadata_procedure):
        self.metadata_procedure =self.auto_generated_string() + metadata_procedure \
            if "#****Begin: Generated Statements***" not in metadata_procedure else metadata_procedure

    def set_data_procedure(self, data_procedure):
        self.data_procedure = self.auto_generated_string() +  data_procedure \
            if "#****Begin: Generated Statements***" not in data_procedure else data_procedure

    def set_epilog_procedure(self, epilog_procedure):
        self.epilog_procedure = self.auto_generated_string() + epilog_procedure \
            if "#****Begin: Generated Statements***" not in epilog_procedure else epilog_procedure

    def set_datasource_type(self, datasource_type):
        self.datasource_type = datasource_type

    def set_datasource_ascii_decimal_seperator(self, datasource_ascii_decimal_separator):
        self.datasource_ascii_decimal_separator = datasource_ascii_decimal_separator

    def set_datasource_ascii_delimiter_char(self, datasource_ascii_delimiter_char):
        self.datasource_ascii_delimiter_char = datasource_ascii_delimiter_char

    def set_datasource_ascii_delimiter_type(self, datasource_ascii_delimiter_type):
        self.datasource_ascii_delimiter_type = datasource_ascii_delimiter_type

    def set_datasource_ascii_header_records(self, datasource_ascii_header_records):
        self.datasource_ascii_header_records = datasource_ascii_header_records

    def set_datasource_ascii_quote_character(self, datasource_ascii_quote_character):
        self.datasource_ascii_quote_character = datasource_ascii_quote_character

    def set_datasource_ascii_thousand_separator(self, datasource_ascii_thousand_separator):
        self.datasource_ascii_thousand_separator = datasource_ascii_thousand_separator

    def set_datasource_data_source_name_for_client(self, datasource_data_source_name_for_client):
        self.datasource_data_source_name_for_client = datasource_data_source_name_for_client

    def set_datasource_data_source_name_for_server(self, datasource_data_source_name_for_server):
        self.datasource_data_source_name_for_server = datasource_data_source_name_for_server

    def set_datasource_password(self, datasource_password):
        self.datasource_password = datasource_password

    def set_datasource_user_name(self, datasource_user_name):
        self.datasource_user_name = datasource_user_name

    def set_datasource_query(self, datasource_query):
        self.datasource_query = datasource_query

    def set_datasource_uses_unicode(self, datasource_uses_unicode):
        self.datasource_uses_unicode = datasource_uses_unicode

    def set_datasource_view(self, datasource_view):
        self.datasource_view = datasource_view

    #construct self.body (json) from the class-attributes
    def construct_body(self):
        # general parameters
        body_as_dict = {'Name': self.name,
                'PrologProcedure': self.prolog_procedure,
                'MetadataProcedure': self.metadata_procedure,
                'DataProcedure': self.data_procedure,
                'EpilogProcedure': self.epilog_procedure,
                'HasSecurityAccess': self.has_security_access,
                'UIData':self.ui_data,
                'DataSource': {},
                'Parameters': self.parameters,
                'Variables': self.variables,
                'VariablesUIData':self.variables_ui_data}

        # specific parameters (depending on datasource type)
        if self.datasource_type == 'ASCII':
            body_as_dict['DataSource'] = {
                "Type": self.datasource_type,
                "asciiDecimalSeparator": self.datasource_ascii_decimal_separator,
                "asciiDelimiterChar": self.datasource_ascii_delimiter_char,
                "asciiDelimiterType": self.datasource_ascii_delimiter_type,
                "asciiHeaderRecords": self.datasource_ascii_header_records,
                "asciiQuoteCharacter": self.datasource_ascii_quote_character,
                "asciiThousandSeparator": self.datasource_ascii_thousand_separator,
                "dataSourceNameForClient": self.datasource_data_source_name_for_client,
                "dataSourceNameForServer": self.datasource_data_source_name_for_server
            }
        elif self.datasource_type == 'None':
            body_as_dict['DataSource'] = {
                "Type": "None"
            }
        elif self.datasource_type == 'ODBC':
            body_as_dict['DataSource'] = {
                "Type": self.datasource_type,
                "dataSourceNameForClient": self.datasource_data_source_name_for_client,
                "dataSourceNameForServer": self.datasource_data_source_name_for_server,
                "userName": self.datasource_user_name,
                "password": self.datasource_password,
                "query": self.datasource_query,
                "usesUnicode": self.datasource_uses_unicode
            }
        elif self.datasource_type == 'TM1CubeView':
            body_as_dict['DataSource'] = {
                "Type": self.datasource_type,
                "dataSourceNameForClient": self.datasource_data_source_name_for_server,
                "dataSourceNameForServer": self.datasource_data_source_name_for_server,
                "view": self.datasource_view
            }
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)


