
'''
TM1py - A python module for TM1
'''

import requests
import logging
import json
import time
from datetime import datetime, date, time, timedelta
import copy
import uuid
import collections
from base64 import b64encode
import sys
if sys.version[0] == '2':
    import httplib as http_client
else:
    import http.client as http_client


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

        :Notes: WIA not implemented.

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
        raise NotImplementedError('not supported')

class TM1pyHTTPClient:
    ''' low level communication with TM1 instance via HTTP.
        based on requests module.

    '''
    def __init__(self, ip, port, login, ssl=True):
        ''' Create an instance of TM1pyHTTPClient

        :param ip: String - address of the TM1 instance
        :param port: Int - HTTPPortNumber as specified in the tm1s.cfg
        :param login: instance of TM1pyLogin
        :param ssl: boolean -  as specified in the tm1s.cfg
        '''
        self._ip = 'localhost' if ip == '' else ip
        self._port = port
        self._ssl = ssl
        self._version = None
        self._headers = {'Connection': 'keep-alive',
                        'User-Agent': 'TM1py',
                        'Content-Type': 'application/json; odata.streaming=true; charset=utf-8',
                        'Accept': 'application/json;odata.metadata=none'}
        # Authorization [Basic, CAM, WIA] through Headers
        if login.auth_type in ['native', 'CAM']:
            self._headers['Authorization'] = login.token
        elif login.auth_type == 'WIA':
            # To be written
            pass
        self._disable_http_warnings()
        self._s = requests.session()
        self._get_cookies()
        # logging
        # http_client.HTTPConnection.debuglevel = 1

    def GET(self, request, data=''):
        ''' Perform a GET request against TM1 instance

        :param request: String, for instance : /api/v1/Cubes?$top=1
        :param data: String, empty
        :return: String, the response as text
        '''

        url, data = self._url_and_body(request=request, data=data)
        r = self._s.get(url=url, headers=self._headers, data=data, verify=False)
        self._verify_response(response=r)
        return r.text

    def POST(self, request, data):
        ''' POST request against the TM1 instance

        :param request: String, /api/v1/Cubes
        :param data: String, the payload (json)
        :return:  String, the response as text
        '''

        url, data = self._url_and_body(request=request, data=data)
        r = self._s.post(url=url, headers=self._headers, data=data, verify=False)
        self._verify_response(response=r)
        return r.text

    def PATCH(self, request, data):
        ''' PATCH request against the TM1 instance

        :param request: String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, the payload (json)
        :return: String, the response as text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.patch(url=url, headers=self._headers, data=data, verify=False)
        self._verify_response(response=r)
        return r.text

    def PUT(self, request, data):
        ''' PUT request against the TM1 instance

        :param request: String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, the payload (json)
        :return: String, the response as text
        '''
        url, data = self._url_and_body(request=request, data=data)
        r = self._s.put(url=url, headers=self._headers, data=data, verify=False)
        self._verify_response(response=r)
        return r.text


    def DELETE(self, request, data=''):
        ''' Delete request against TM1 instance

        :param request:  String, for instance : /api/v1/Dimensions('plan_business_unit')
        :param data: String, empty
        :return: String, the response in text

        '''

        url, data = self._url_and_body(request=request, data=data)
        r = self._s.delete(url=url, headers=self._headers, data=data, verify=False)
        self._verify_response(response=r)
        return r.text

    def _get_cookies(self):
        ''' perform a simple GET request (Ask for the TM1 Version) to start a session

        '''
        if self._ssl:
            url = 'https://' + self._ip + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        else:
            url = 'http://' + self._ip + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        response = self._s.get(url=url, headers=self._headers, data='', verify=False)
        self._verify_response(response)
        self._version = json.loads(response.text)['value']

    def _url_and_body(self, request, data):
        ''' create proper url and payload

        '''
        if self._ssl:
            url = 'https://' + self._ip + ':' + str(self._port) + request
        else:
            url = 'http://' + self._ip + ':' + str(self._port) + request
        url = url.replace(' ', '%20').replace('#', '%23')
        data = data.encode('utf-8')
        return url, data

    def _verify_response(self, response):
        ''' check if Status Code is OK

        :Parameters:
            `response`: String
                the response that is returned from a method call

        :Exceptions:
            TM1pyException, raises TM1pyException when Code is not 200, 204 etc.
        '''
        if not response.ok:
            raise TM1pyException(response.text, status_code=response.status_code, reason=response.reason)

    def _disable_http_warnings(self):
        # disable HTTP verification warnings from requests library
        requests.packages.urllib3.disable_warnings()


class TM1pyQueries:
    ''' Class offers Queries to interact with a TM1 Server.

    - CRUD Features for all type of TM1 objects (Cube, Process, Dimension, etc.)
        Create method - `create` prefix
        Read methods - `get` prefix
        Update methods - `update prefix`
        Delete methods - `delete prefix`

    - Additional Features
        Retrieve and write data into TM1
        Execute Process, Chore or TI Code
        Query Messagelog
        Generate MDX from existing Cubeviews
        ...
    '''

    def __init__(self, ip, port, login, ssl=True):
        ''' Constructor, Create an instance of TM1pyQueries

        :param ip: String, the IP address of the TM1 Server
        :param port: Int, HttpPortNumber as specified in the tm1s.cfg
        :param login: Instance of TM1pyLogin
        :param ssl: Boolean, as specified in the tm1s.cfg
        '''
        self._ip = ip
        self._port = port
        self._login = login
        self._ssl = ssl
        self._client = TM1pyHTTPClient(ip=ip, port=port, login=login, ssl=ssl)

    def __enter__(self):
        return self

    def __exit__(self,exception_type, exception_value, traceback):
        self.logout()

    def logout(self):
        ''' End TM1 Session and HTTP session

        '''
        try:
            # ProductVersion >= TM1 10.2.2 FP 6
            self._client.POST('/api/v1/ActiveSession/tm1.Close', '')

        except TM1pyException:
            # ProductVersion < TM1 10.2.2 FP 6
            self._client.POST('/api/logout', '')

    def get_server_name(self):
        ''' Ask TM1 Server for its name

        :Returns:
            String, the server name
        '''
        request = '/api/v1/Configuration/ServerName'
        response = self._client.GET(request, '')
        return json.loads(response)['value']

    def get_product_version(self):
        """ Ask TM1 Server for its version

        :Returns:
            String, the version
        """
        request = '/api/v1/Configuration/ProductVersion'
        response = self._client.GET(request, '')
        return json.loads(response)['value']

    def write_value(self, cube_name, dimension_order, element_tuple, value):
        """ Write value into cube at specified coordinates

        :param cube_name: name of the target cube
        :param dimension_order: dimension names in their correct order
        :param element_tuple: target coordinates
        :param value: the actual value
        :return: response
        """

        request = "/api/v1/Cubes('{}')/tm1.Update".format(cube_name)
        body_as_dict = collections.OrderedDict()
        body_as_dict["Cells"] = [{}]
        body_as_dict["Cells"][0]["Tuple@odata.bind"] = \
            ["Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dim, dim, elem)
             for dim, elem in zip(dimension_order, element_tuple)]
        body_as_dict["Value"] = str(value)
        data = json.dumps(body_as_dict)
        return self._client.POST(request=request, data=data)

    def write_values(self, cube_name, cellset_as_dict):
        """ Write values in cube

        :param cube_name: name of the cube
        :param cellset_as_dict: {(elem_a, elem_b, elem_c): 243, (elem_d, elem_e, elem_f) : 109}
        :return:
        """
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

    def get_all_cube_names(self):
        """ Ask TM1 Server for list with all cube names

        :return: List of Strings
        """
        response = self._client.GET('/api/v1/Cubes?$select=Name', '')
        cubes = json.loads(response)['value']
        list_cubes = list(entry['Name'] for entry in cubes)
        return list_cubes

    def get_all_dimension_names(self):
        '''Ask TM1 Server for list with all dimension names

        :Returns:
            List of Strings
        '''
        response = self._client.GET('/api/v1/Dimensions?$select=Name', '')
        dimensions = json.loads(response)['value']
        list_dimensions = list(entry['Name'] for entry in dimensions)
        return list_dimensions

    def execute_process(self, name_process, parameters=''):
        """ Ask TM1 Server to execute a process

        :param name_process:
        :param parameters: String, for instance {"Parameters": [ { "Name": "pLegalEntity", "Value": "UK01" }] }
        :return:
        """

        data = json.dumps(parameters)
        return self._client.POST("/api/v1/Processes('" + name_process + "')/tm1.Execute", data=data)

    def execute_chore(self, name_chore):
        """ Ask TM1 Server to execute a chore

            :param name_chore: String, name of the chore to be executed
            :return: String, the response
        """
        return self._client.POST("/api/v1/Chores('" + name_chore + "')/tm1.Execute", '')

    def execute_TI_code(self, lines_prolog, lines_epilog):
        ''' Execute lines of code on the TM1 Server

            :param lines_prolog: list - where each element is a valid line of TI code.
            :param lines_epilog: list - where each element is a valid line of TI code.
        '''
        process_name = '}' + 'TM1py' + str(uuid.uuid4())
        p = Process(name=process_name,
                    prolog_procedure=Process.auto_generated_string + '\r\n'.join(lines_prolog),
                    epilog_procedure=Process.auto_generated_string + '\r\n'.join(lines_epilog))
        self.create_process(p)
        try:
            self.execute_process(process_name)
            pass
        except TM1pyException as e:
            raise e
        finally:
            self.delete_process(process_name)

    def execute_mdx(self, mdx, cube_name=None, cell_properties=None, top=None):
        """

        :param mdx: MDX Query, as string
        :param cube_name: optional. If not given, parse mdx. can be costly.
        :param cell_properties: properties to be queried from the cell. Like Value, Ordinal, etc as iterable
        :param top: integer
        :return: content in sweet consice strcuture.
        """
        if not cell_properties:
            cell_properties = ['Value', 'Ordinal']
        if top:
            request = '/api/v1/ExecuteMDX?$expand=Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName);$top={})),Cells($select={};$top={})'\
                .format(str(top), ','.join(cell_properties), str(top))
        else:
            request = '/api/v1/ExecuteMDX?$expand=Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName))),Cells($select={})'\
                .format(','.join(cell_properties))
        data = {
            'MDX': mdx
        }
        if not cube_name:
            cube_name = TM1pyUtils.read_cube_name_from_mdx(mdx)
        dimension_order = self.get_dimension_order(cube_name)
        cellset = self._client.POST(request=request,data=json.dumps(data))
        return TM1pyUtils.build_content_from_cellset(dimension_order=dimension_order,
                                                     cellset_as_dict=json.loads(cellset),
                                                     cell_properties=cell_properties,
                                                     top=top)

    def get_last_message_log_entries(self, reverse=True, top=None):
        reverse = 'true' if reverse else 'false'
        request = '/api/v1/MessageLog(Reverse={})'.format(reverse)
        if top:
            request += '?$top={}'.format(top)
        response = self._client.GET(request, '')
        return json.loads(response)['value']

    def get_last_process_message_from_messagelog(self, process_name):
        ''' get the latest messagelog entry for a process

            :param process_name: name of the process
            :return: String - the message, for instance: "Ausführung normal beendet, verstrichene Zeit 0.03  Sekunden"
        '''
        request = "/api/v1/MessageLog()?$orderby='TimeStamp'&$filter=Logger eq 'TM1.Process' " \
                  "and contains( Message, '" + process_name + "')"
        response = self._client.GET(request=request)
        response_as_list = json.loads(response)['value']
        if len(response_as_list) > 0:
            message_log_entry = response_as_list[0]
            return message_log_entry['Message']


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
        ''' get all ProcessErrorLog entries for a process

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
        request = "/api/v1/Processes('" + name_process + "')"
        response = self._client.DELETE(request, "")
        return response

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
        response = self._client.GET('/api/v1/Processes?$select=Name', '')
        dict_processes = json.loads(response)['value']
        processes = list(process['Name'] for process in dict_processes)
        return processes

    # TODO Redesign required!
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
        """ Get a process from TM1 Server

        :param name_process:
        :return: Instance of the TM1py.Process
        """
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

    def get_all_processes(self):
        """ Get a processes from TM1 Server

        :param name_process:
        :return: List, instances of the TM1py.Process
        """
        request="/api/v1/Processes?$select=*,UIData,VariablesUIData," \
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
        response_as_dict= json.loads(response)
        return [Process.from_dict(p) for p in response_as_dict['value']]

    def update_process(self, process):
        ''' update an existing Process on TM1 Server

        :Parameters:
            `process`: Instance of TM1py.Process class

        :Returns:
            `string` : the response
        '''
        request = "/api/v1/Processes('" + process.name + "')"
        response = self._client.PATCH(request, process.body)
        return response

    def create_process(self, process):
        ''' post a new process against TM1 Server

        :Parameters:
            `process`: Instance of TM1py.Process class

        :Returns:
            `string` : the response
        '''
        request = "/api/v1/Processes"
        response = self._client.POST(request, process.body)
        return response

    def create_view(self, view, private=True):
        ''' create a new view on TM1 Server

        :Parameters:
            `view`: instance of subclass of TM1py.View (TM1py.NativeView or TM1py.MDXView)
            `private`: boolean

        :Returns:
            `string` : the response
        '''
        views = "PrivateViews" if private else "Views"
        request = "/api/v1/Cubes('{}')/{}".format(view.cube, views)
        return self._client.POST(request, view.body)

    def view_exists(self, cube_name, view_name):
        ''' checks if view exists

        :param cube_name:  string, name of the cube
        :param view_name: string, name of the view

        :return True or False
        '''
        private, public = False, False
        try:
            self._client.GET("/api/v1/Cubes('{}')/PrivateViews('{}')".format(cube_name, view_name))
            private = True
        except TM1pyException:
            pass
        try:
            self._client.GET("/api/v1/Cubes('{}')/Views('{}')".format(cube_name, view_name))
            public = True
        except TM1pyException:
            pass
        return private, public

    def get_native_view(self, cube_name, view_name, private=True):
        ''' get a NativeView from TM1 Server

        :param cube_name:  string, name of the cube
        :param view_name:  string, name of the native view
        :param private:    boolean

        :return: instance of TM1py.NativeView
        '''
        views = "PrivateViews" if private else "Views"
        request = "/api/v1/Cubes('" + cube_name + "')/" + views + "('" + view_name + "')?$expand=" \
                  "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name, Alias),  " \
                  "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name,Alias), " \
                  "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name,Alias), " \
                  "tm1.NativeView/Titles/Selected($select=Name)"
        view_as_json = self._client.GET(request)
        native_view = NativeView.from_json(view_as_json, cube_name)
        return native_view

    def get_mdx_view(self, cube_name, view_name, private=True):
        ''' get an MDXView from TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the MDX view
        :param private: boolean

        :return: instance of TM1py.MDXView
        '''
        if private:
            request = "/api/v1/Cubes('{}')/PrivateViews('{}')?$expand=*".format(cube_name, view_name)
        else:
            request = "/api/v1/Cubes('{}')/Views('{}')?$expand=*".format(cube_name, view_name)
        view_as_json = self._client.GET(request)
        mdx_view = MDXView.from_json(view_as_json=view_as_json)
        return mdx_view

    def get_all_views(self, cube_name):
        """ get all public and private views from cube.

        :param cube_name: String, name of the cube.
        :return: 2 Lists of TM1py.View instances, private views, public views
        """
        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            request = "/api/v1/Cubes('" + cube_name + "')/" + view_type + "?$expand=" \
                      "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name, Alias),  " \
                      "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name,Alias), " \
                      "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name,Alias), " \
                      "tm1.NativeView/Titles/Selected($select=Name)"
            response = self._client.GET(request)
            response_as_list = json.loads(response)['value']
            for view_as_dict in response_as_list:
                if view_as_dict['@odata.type'] == '#ibm.tm1.api.v1.MDXView':
                    view = MDXView.from_dict(view_as_dict, cube_name)
                else:
                    view = NativeView.from_dict(view_as_dict, cube_name)
                if view_type == "PrivateViews":
                    private_views.append(view)
                else:
                    public_views.append(view)
        return private_views, public_views

    def update_view(self, view, private=True):
        ''' update an existing view

        :param view: instance of TM1py.NativeView or TM1py.MDXView
        :return: response
        '''
        if isinstance(view, MDXView):
            return self._update_mdx_view(view, private)
        if isinstance(view, NativeView):
            return self._update_native_view(view, private)
        else:
            raise Exception('given object is not of type MDXView or NativeView')

    def _update_mdx_view(self, mdx_view, private):
        ''' update an mdx view on TM1 Server

        :param mdx_view: instance of TM1py.MDXView
        :param private: boolean

        :return: string, the response
        '''
        if private:
            request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(mdx_view.cube, mdx_view.name)
        else:
            request = "/api/v1/Cubes('{}')/Views('{}')".format(mdx_view.cube, mdx_view.name)
        response = self._client.PATCH(request, mdx_view.body)
        return response

    def _update_native_view(self, native_view, private=True):
        ''' update a native view on TM1 Server

        :param view: instance of TM1py.NativeView
        :param private: boolean

        :return: string, the response
        '''
        if private:
            request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(native_view.cube, native_view.name)
        else:
            request = "/api/v1/Cubes('{}')/Views('{}')".format(native_view.cube, native_view.name)
        response = self._client.PATCH(request, native_view.body)
        return response


    def delete_view(self, cube_name, view_name, private=True):
        ''' delete an existing view (MDXView or NativeView) on the TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: Boolean

        :return: String, the response
        '''
        if private:
            request = "/api/v1/Cubes('{}')/PrivateViews('{}')".format(cube_name, view_name)
        else:
            request = "/api/v1/Cubes('{}')/Views('{}')".format(cube_name, view_name)
        response = self._client.DELETE(request)
        return response


    def get_elements_filtered_by_attribute(self, dimension_name, hierarchy_name, attribute_name, attribute_value):
        ''' get all elements from a hierarchy with given attribute value

        :param dimension_name:
        :param hierarchy_name:
        :param attribute_name:
        :param attribute_value:
        :return: List of element names
        '''
        attribute_name = attribute_name.replace(" ", "")
        if isinstance(attribute_value, str):
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = Attributes/{} eq '{}';$select=Name)".\
                format(dimension_name, hierarchy_name,attribute_name, attribute_value)
        else:
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = Attributes/{} eq {};$select=Name)"\
                .format(dimension_name, hierarchy_name,attribute_name, attribute_value)
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        return [elem['Name'] for elem in response_as_dict['Elements']]

    def dimension_exists(self, dimension_name):
        """ check if dimension exists

        :param dimension_name:
        :return: Boolean
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, dimension_name)
        try:
            self._client.GET(request, '')
            return True
        except TM1pyException:
            return False

    def create_dimension(self, dimension):
        ''' create a dimension

        :param dimension: instance of TM1py.Dimension
        :return: response
        '''

        # if not all calls successfull -> redo everything that has been done in this function
        try:
            # create Dimension, Hierarchies, Elements, Edges etc.
            request = "/api/v1/Dimensions"
            response = self._client.POST(request, dimension.body)
            # create ElementAttributes. Cant be done in the same request as Creating the Hierarchies.
            for hierarchy in dimension.hierarchies:
                self.update_hierarchy_attributes(hierarchy)
        except TM1pyException as e:
            # redo everything if problem in step 1 or 2
            if self.dimension_exists(dimension.name):
                self.delete_dimension(dimension.name)
            raise e
        return response

    def get_dimension(self, dimension_name):
        """

        :param dimension_name:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')?$expand=Hierarchies($expand=*)'.format(dimension_name)
        dimension_as_json = self._client.GET(request)
        return Dimension.from_json(dimension_as_json)

    def update_dimension(self, dimension):
        """ update an existing dimension

        :param dimension: instance of TM1py.Dimension
        :return: None
        """
        # update Hierarchies
        for hierarchy in dimension:
            self.update_hierarchy(hierarchy)

    def delete_dimension(self, dimension_name):
        ''' delete a dimension

        :param dimension_name:
        :return:
        '''
        request = '/api/v1/Dimensions(\'{}\')'.format(dimension_name)
        return self._client.DELETE(request)

    def create_hierarchy(self, hierarchy):
        """ create a hierarchy in a dimension

        :param hierarchy:
        :return:
        """
        raise NotImplementedError('not supported')

    def get_element_attributes(self, dimension_name, hierarchy_name):
        """ get element attributes from hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/ElementAttributes'.format(dimension_name,
                                                                                            hierarchy_name)
        response = self._client.GET(request,'')
        element_attributes = [ElementAttribute.from_dict(ea) for ea in json.loads(response)['value']]
        return element_attributes

    def get_hierarchy(self, dimension_name, hierarchy_name):
        """ get hierarchy

        :param dimension_name: name of the dimension
        :param hierarchy_name: name of the hierarchy
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        response = self._client.GET(request, '')
        return response

    def update_hierarchy(self, hierarchy):
        """ update a hierarchy

        :param hierarchy: instance of TM1py.Hierarchy
        :return:
        """
        # update Hierarchy
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(hierarchy.dimension_name, hierarchy.name)
        response = self._client.PATCH(request, hierarchy.body)
        return self.update_hierarchy_attributes(hierarchy=hierarchy)

    def update_hierarchy_attributes(self, hierarchy):
        """ update elementsattributes of a hierarchy

        :param hierarchy: instance of TM1py.Hierarchy
        :return:
        """
        # get existing attributes first.
        element_attribute_names = [ea.name for ea in self.get_element_attributes(dimension_name=hierarchy.dimension_name,
                                                                                 hierarchy_name=hierarchy.name)]
        # only write ElementAttributes that dont already exist !
        for element_attribute in filter(lambda ea: ea.name not in element_attribute_names,
                                        hierarchy.element_attributes):
            self.create_element_attribute(dimension_name=hierarchy.dimension_name,
                                          hierarchy_name=hierarchy.name,
                                          element_attribute=element_attribute)

    def create_element_attribute(self, dimension_name, hierarchy_name, element_attribute):
        """ like AttrInsert

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/ElementAttributes'.format(dimension_name,
                                                                                            hierarchy_name)
        return self._client.POST(request, element_attribute.body)

    def delete_hierarchy(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')'.format(dimension_name, hierarchy_name)
        return self._client.DELETE(request, '')

    def get_all_annotations_from_cube(self, name_cube):
        """ get all annotations from given cube as a List.

        :param name_cube:
        :return: list of instances of TM1py.Annotation
        """
        request = "/api/v1/Cubes('{}')/Annotations?$expand=DimensionalContext($select=Name)".format(name_cube)
        response = self._client.GET(request, '')
        annotations_as_dict = json.loads(response)['value']
        annotations = [Annotation.from_json(json.dumps(element)) for element in annotations_as_dict]
        return annotations

    def get_view_content(self, cube_name, view_name, cell_properties=None, private=True, top=None):
        """ get view content as dictionary with sweet and concise structure.
            Works on NativeView and MDXView !
            Not Hierarchy aware !

        :param cube_name: String
        :param view_name: String
        :param cell_properties: List, cell properties: [Values, Status, HasPicklist, etc.]
        :param private: Boolean
        :param top: Int, number of cells

        :return: Dictionary : {([dim1].[elem1], [dim2][elem6]): {'Value':3127.312, 'Ordinal':12}   ....  }
        """
        if not cell_properties:
            cell_properties = ['Value','Ordinal']
        dimension_order = self.get_dimension_order(cube_name)
        cellset_as_dict = self._get_cellset_from_view(cube_name, view_name, cell_properties, private, top)
        content_as_dict = TM1pyUtils.build_content_from_cellset(dimension_order, cellset_as_dict, cell_properties, top)
        return content_as_dict

    def _get_cellset_from_view(self, cube_name, view_name, cell_properties=None, private=True, top=None):
        """ get view content as dictionary in its native (cellset-) structure.

        :param cube_name: String
        :param view_name: String
        :param cell_properties: List of cell properties
        :param private: Boolean
        :param top: Int, number of cells

        :return:
            `Dictionary` : {Cells : {}, 'ID' : '', 'Axes' : [{'Ordinal' : 1, Members: [], ...},
            {'Ordinal' : 2, Members: [], ...}, {'Ordinal' : 3, Members: [], ...} ] }
        """
        if not cell_properties:
            cell_properties = ['Value','Ordinal']
        views = 'PrivateViews' if  private else 'Views'
        if top:
            request = '/api/v1/Cubes(\'{}\')/{}(\'{}\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName);$top={})),Cells($select={};$top={})'\
                .format(cube_name, views, view_name, str(top), ','.join(cell_properties), str(top))
        else:
            request = '/api/v1/Cubes(\'{}\')/{}(\'{}\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members' \
                      '($select=UniqueName))),Cells($select={})'\
                .format(cube_name, views, view_name, ','.join(cell_properties))
        response = self._client.POST(request, '')
        return json.loads(response)


    def get_dimension_order(self, cube_name):
        """ get name of the dimensions of a cube in their correct order

        :param cube_name: String
        :return:  List : [dim1, dim2, dim3, etc.]
        """
        response = self._client.GET('/api/v1/Cubes(\'' + cube_name + '\')/Dimensions?$select=Name', '')
        response_as_dict = json.loads(response)['value']
        dimension_order = [element['Name'] for element in response_as_dict]
        return dimension_order

    def create_annotation(self, annotation):
        """ create an Annotation

            :param annotation: instance of TM1py.Annotation
            :return string: the response
        """
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

    def get_annotation(self, id):
        ''' get an annotation from any cube in TM1 Server through its id

            :param id: String, the id of the annotation

            :return:
                Annotation: an instance of TM1py.Annoation
        '''
        request = "/api/v1/Annotations('{}')?$expand=DimensionalContext($select=Name)".format(id)
        annotation_as_json = self._client.GET(request=request)
        return Annotation.from_json(annotation_as_json)


    def update_annotation(self, annotation):
        ''' update Annotation on TM1 Server

            :param annotation: instance of TM1py.Annotation

            :Notes:
                updateable attributes:
                    commentValue
        '''
        request = "/api/v1/Annotations('{}')".format(annotation._id)
        return self._client.PATCH(request=request, data=annotation.body)

    def delete_annotation(self, id):
        ''' delete Annotation on TM1 Server

            :param id: string, the id of the annotation

            :return:
                string: the response
        '''
        request = "/api/v1/Annotations('{}')".format(id)
        return self._client.DELETE(request=request)

    def create_subset(self, subset, private=True):
        ''' create subset on the TM1 Server

            :param subset: TM1py.Subset, the subset that shall be created

            :return:
                string: the response
        '''
        subsets = "PrivateSubsets" if private else "Subsets"
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/{}'\
            .format(subset._dimension_name, subset._dimension_name, subsets)
        response = self._client.POST(request, subset.body)
        return response

    def get_subset(self, dimension_name, subset_name, private=True):
        """ get a subset from the TM1 Server

            :param dimension_name: string, name of the dimension
            :param subset_name: string, name of the subset
            :param private: Boolean

            :return: instance of TM1py.Subset
        """
        subsets = "PrivateSubsets" if private else "Subsets"
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/{}(\'{}\')?$expand=' \
                  'Hierarchy($select=Dimension),' \
                  'Elements($select=Name)&$select=*,Alias'.format(dimension_name, dimension_name, subsets, subset_name)
        response = self._client.GET(request=request)
        return Subset.from_json(response)

    def get_all_subset_names(self, dimension_name, hierarchy_name, private=True):
        """ get names of all private or public subsets in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param private: Boolean
        :return: List of Strings
        """
        subsets = "PrivateSubsets" if private else "Subsets"
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/{}?$select=Name'\
            .format(dimension_name, hierarchy_name, subsets)
        response = self._client.GET(request=request)
        subsets = json.loads(response)['value']
        return [subset['Name'] for subset in subsets]

    def update_subset(self, subset, private=True):
        """ update a subset on the TM1 Server

        :param subset: instance of TM1py.Subset.
        :param private: Boolean
        :return: response
        """

        if private:
            # just delete it and rebuild it, since there are no dependencies
            return self._update_private_subset(subset)

        else:
            # update it. Clear Elements with evil workaround
            return self._update_public_subset(subset)

    def _update_private_subset(self, subset):
        """ update a private subset on the TM1 Server

        :param subset: instance of TM1py.Subset
        :return: response
        """
        # delete it
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/PrivateSubsets(\'{}\')' \
            .format(subset._dimension_name, subset._dimension_name, subset._subset_name)
        self._client.DELETE(request, '')
        # rebuild it
        return self.create_subset(subset, True)

    def _update_public_subset(self, subset):
        """ update a public subset on the TM1 Server

        :param subset: instance of TM1py.Subset
        :return: response
        """
        # clear elements of subset. evil workaround! Should be done through delete on the Elements Collection
        ti = lines_prolog = "SubsetDeleteAllElements(\'{}\', \'{}\');".format(subset.dimension_name, subset.name)
        self.execute_TI_code(lines_prolog=ti, lines_epilog='')

        # update subset
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Subsets(\'{}\')' \
            .format(subset._dimension_name, subset._dimension_name, subset._subset_name)
        return self._client.PATCH(request=request, data=subset.body)

    def delete_subset(self, dimension_name, subset_name, private=True):
        """ delete a subset on the TM1 Server

        :param dimension_name: String, name of the dimension
        :param subset_name: String, name of the subset
        :param private: Boolean
        :return:
        """
        subsets = "PrivateSubsets" if private else "Subsets"
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/{}(\'{}\')'\
            .format(dimension_name, dimension_name, subsets, subset_name)
        response = self._client.DELETE(request=request, data='')
        return response

    def get_threads(self):
        ''' return a dict of threads from the TM1 Server

            :return:
                dict: the response
        '''
        try:
            request = '/api/v1/Threads'
            response = self._client.GET(request)
            response_as_dict = json.loads(response)['value']
            return response_as_dict
        except (ConnectionError, ConnectionAbortedError):
            self._client = TM1pyHTTPClient(self._ip, self._port, self._login, self._ssl)


    def get_chore(self, chore_name):
        """ get a chore from the TM1 Server

        :param chore_name:
        :return: instance of TM1py.Chore
        """
        request = "/api/v1/Chores('{}')?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))".format(chore_name)
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        return Chore.from_dict(response_as_dict)

    def get_all_chores(self):
        """ get a List of all Chores

        :return: List of TM1py.Chore
        """
        request = "/api/v1/Chores?$expand=Tasks($expand=*,Process($select=Name),Chore($select=Name))"
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        return [Chore.from_dict(chore_as_dict) for chore_as_dict in response_as_dict['value']]


    def create_chore(self, chore):
        """ create chore in TM1

        :param chore: instance of TM1py.Chore
        :return:
        """
        request = "/api/v1/Chores"
        response = self._client.POST(request, chore.body)
        if chore._active is True:
            self.activate_chore(chore._name)
        return response

    def delete_chore(self, chore_name):
        """ delete chore in TM1

        :param chore_name:
        :return: response
        """

        request = "/api/v1/Chores('{}')".format(chore_name)
        response = self._client.DELETE(request)
        return response

    def update_chore(self, chore):
        ''' update chore on TM1 Server

        does not update: DST Sensitivity!
        :param chore:
        :return: response
        '''
        try:
            # deactivate
            self.deactivate_chore(chore._name)

            # update StartTime, ExecutionMode, Frequency
            request = "/api/v1/Chores('{}')".format(chore._name)
            self._client.PATCH(request, chore.body)

            # update Tasks
            for i, task_new in enumerate(chore._tasks):
                task_old =  self.get_chore_task(chore._name, i)
                if task_old is None:
                    self.create_chore_task(chore._name, task_new)
                elif task_new != task_old:
                    self.update_chore_task(chore._name, task_new)
        finally:
            # activate
            if chore._active:
                self.activate_chore(chore._name)

    def activate_chore(self, chore_name):
        """ active chore on TM1 Server

        :param chore_name:
        :return: response
        """
        request = "/api/v1/Chores('{}')/tm1.Activate".format(chore_name)
        return self._client.POST(request, '')

    def deactivate_chore(self, chore_name):
        """ deactive chore on TM1 Server

        :param chore_name:
        :return: response
        """

        request = "/api/v1/Chores('{}')/tm1.Deactivate".format(chore_name)
        return self._client.POST(request, '')

    def set_chore_local_start_time(self, chore_name, datetime):
        """ Makes Server crash if chore is active (FP6) :)

        :param chore_name:
        :param datetime:
        :return:
        """
        request = "/api/v1/Chores('{}')/tm1.SetServerLocalStartTime".format(chore_name)
        # function for 3 to '03'
        fill = lambda t: str(t).zfill(2)
        data = {
            "StartDate": "{}-{}-{}".format(datetime.year, datetime.month, datetime.day),
            "StartTime": "{}:{}:{}".format(fill(datetime.hour), fill(datetime.minute), fill(datetime.second))
        }
        return self._client.POST(request, json.dumps(data))

    def get_chore_task(self, chore_name, step):
        """ get task from chore

        :param chore_name: name of the chore
        :param step: integer
        :return: instance of TM1py.ChoreTask
        """
        request = "/api/v1/Chores('{}')/Tasks({})?$expand=*,Process($select=Name),Chore($select=Name)".format(chore_name, step)
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        return ChoreTask.from_dict(response_as_dict)

    def create_chore_task(self, chore_name, chore_task):
        """ create Chore task on TM1 Server

        :param chore_name: name of Chore to update
        :param chore_task: instance of TM1py.ChoreTask
        :return: response
        """
        request = "/api/v1/Chores('{}')/Tasks".format(chore_name)
        chore_task_body_as_string = json.dumps(chore_task.body, ensure_ascii=False, sort_keys=False)
        response = self._client.POST(request, chore_task_body_as_string)
        return response

    def update_chore_task(self, chore_name, chore_task):
        """ update a chore task

        :param chore_name: name of the Chore
        :param chore_task: instance TM1py.ChoreTask
        :return: response
        """
        request = "/api/v1/Chores('{}')/Tasks({})".format(chore_name, chore_task._step)
        chore_task_body_as_string = json.dumps(chore_task.body, ensure_ascii=False, sort_keys=False)
        response = self._client.PATCH(request, chore_task_body_as_string)
        return response

    def create_user(self, user):
        """ create a user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        request = '/api/v1/Users'
        self._client.POST(request, user.body)

    def get_user(self, user_name):
        """ get user from TM1 Server

        :param user_name:
        :return: instance of TM1py.User
        """
        request = '/api/v1/Users(\'{}\')?$expand=Groups'.format(user_name)
        response = self._client.GET(request)
        return User.from_json(response)

    def update_user(self, user):
        """ update user on TM1 Server

        :param user: instance of TM1py.User
        :return: response
        """
        for current_group in self.get_groups_from_user(user.name):
            if current_group not in user.groups:
                self.remove_user_from_group(current_group, user.name)
        request = '/api/v1/Users(\'{}\')'.format(user.name)
        return self._client.PATCH(request, user.body)

    def delete_user(self, user_name):
        """ delete user on TM1 Server

        :param user_name:
        :return: response
        """
        request = '/api/v1/Users(\'{}\')'.format(user_name)
        return self._client.DELETE(request)

    def get_all_users(self):
        """ get all users from TM1 Server

        :return: List of TM1py.User instances
        """
        request = '/api/v1/Users?$expand=Groups'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['value']]
        return users

    def get_active_users(self):
        """ get the active users in TM1 Server

        :return: List of TM1py.User instances
        """
        request = '/api/v1/Users?$filter=IsActive eq true&$expand=Groups'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['value']]
        return users

    def user_is_active(self, user_name):
        """ check if user is currently active in TM1

        :param user_name:
        :return: Boolean
        """
        request = "/api/v1/Users('{}')/IsActive".format(user_name)
        response = self._client.GET(request)
        return json.loads(response)['value']

    def get_users_from_group(self, group_name):
        """ get all users from group

        :param group_name:
        :return: List of TM1py.User instances
        """
        request = '/api/v1/Groups(\'{}\')?$expand=Users($expand=Groups)'.format(group_name)
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        users = [User.from_dict(user) for user in response_as_dict['Users']]
        return users

    def get_groups_from_user(self, user_name):
        """ get the groups of a user in TM1 Server

        :param user_name:
        :return: List of strings
        """
        request = '/api/v1/Users(\'{}\')/Groups'.format(user_name)
        response = self._client.GET(request)
        groups = json.loads(response)['value']
        return [group['Name'] for group in groups]

    def remove_user_from_group(self, group_name, user_name):
        """ remove user from group in TM1 Server

        :param group_name:
        :param user_name:
        :return: response
        """
        request = '/api/v1/Users(\'{}\')/Groups?$id=Groups(\'{}\')'.format(user_name, group_name)
        return self._client.DELETE(request)

    def get_all_groups(self):
        """ get all groups from TM1 Server

        :return: List of strings
        """

        request = '/api/v1/Groups?$select=Name'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        groups = [entry['Name'] for entry in response_as_dict['value']]
        return groups

    def create_cube(self, cube):
        """ create new cube on TM1 Server

        :param cube:
        :return: response
        """
        request = '/api/v1/Cubes'
        return self._client.POST(request, cube.body)


    def get_cube(self, cube_name):
        """ get cube from TM1 Server

        :param cube_name:
        :return: instance of TM1py.Cube
        """

        request = '/api/v1/Cubes(\'{}\')?$expand=Dimensions($select=Name)'.format(cube_name)
        response = self._client.GET(request)
        cube = Cube.from_json(response)
        return cube

    def get_all_cubes(self):
        """ get all cubes from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = '/api/v1/Cubes?$expand=Dimensions($select=Name)'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def get_model_cubes(self):
        """ get all Cubes without } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = '/api/v1/ModelCubes()?$expand=Dimensions($select=Name)'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def get_control_cubes(self):
        """ get all Cubes with } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = '/api/v1/ControlCubes()?$expand=Dimensions($select=Name)'
        response = self._client.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def update_cube(self, cube):
        """ update existing cube on TM1 Server

        :param cube: instance of TM1py.Cube
        :return: response
        """
        request = '/api/v1/Cubes(\'{}\')'.format(cube.name)
        return self._client.PATCH(request, cube.body)

    def delete_cube(self, cube_name):
        """ delete a cube in TM1

        :param cube_name:
        :return: response
        """
        request = '/api/v1/Cubes(\'{}\')'.format(cube_name)
        return self._client.DELETE(request)

class TM1pyUtils:
    @staticmethod
    def get_all_servers_from_adminhost(adminhost='localhost'):
        """ Ask Adminhost for TM1 Servers

        :param adminhost: IP or DNS Alias of the adminhost
        :return: List of Servers (instances of the TM1py.Server class)
        """

        conn = http_client.HTTPConnection(adminhost, 5895)
        request = '/api/v1/Servers'
        conn.request('GET', request, body='')
        response = conn.getresponse().read().decode('utf-8')
        response_as_dict = json.loads(response)
        servers = []
        for server_as_dict in response_as_dict['value']:
            server = Server(server_as_dict)
            servers.append(server)
        return servers

    @staticmethod
    def read_cube_name_from_mdx(mdx):
        """ read the cubename from a valid MDX Query

        :param mdx: The MDX Query as String
        :return: String, name of a cube
        """

        mdx_trimed = ''.join(mdx.split()).upper()
        pos_oncolumnsfrom = mdx_trimed.rfind("FROM[") + len("FROM[")
        pos_where = mdx_trimed.find("]WHERE", pos_oncolumnsfrom)
        return mdx_trimed[pos_oncolumnsfrom:pos_where]

    @staticmethod
    def sort_addresstuple(dimension_order, unsorted_addresstuple):
        ''' Sort the given mixed up addresstuple

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

    @staticmethod
    def build_content_from_cellset(dimension_order, cellset_as_dict, cell_properties, top):
        """ transform cellset data into concise dictionary

        :param dimension_order:
        :param cellset_as_dict:
        :param cell_properties:
        :param top: Maximum Number of cells
        :return:
        """
        content_as_dict = {}

        axe0_as_dict = cellset_as_dict['Axes'][0]
        axe1_as_dict = cellset_as_dict['Axes'][1]

        ordinal_cells = 0

        ordinal_axe2 = 0
        # get coordinates on axe 2: Title
        # if there are no elements on axe 2 assign empty list to elements_on_axe2
        if len(cellset_as_dict['Axes']) > 2:
            axe2_as_dict = cellset_as_dict['Axes'][2]
            Tuples_as_dict = axe2_as_dict['Tuples'][ordinal_axe2]['Members']
            elements_on_axe2 = [data['UniqueName'] for data in Tuples_as_dict]
        else:
            elements_on_axe2 = []

        ordinal_axe1 = 0
        for i in range(axe1_as_dict['Cardinality']):
            # get coordinates on axe 1: Rows
            Tuples_as_dict = axe1_as_dict['Tuples'][ordinal_axe1]['Members']
            elements_on_axe1 = [data['UniqueName'] for data in Tuples_as_dict]
            ordinal_axe0 = 0
            for j in range(axe0_as_dict['Cardinality']):
                # get coordinates on axe 0: Columns
                Tuples_as_dict = axe0_as_dict['Tuples'][ordinal_axe0]['Members']
                elements_on_axe0 = [data['UniqueName'] for data in Tuples_as_dict]
                coordinates = elements_on_axe0 + elements_on_axe2 + elements_on_axe1
                coordinates_sorted = TM1pyUtils.sort_addresstuple(dimension_order, coordinates)
                # get cell properties
                content_as_dict[coordinates_sorted] = {}
                for cell_property in cell_properties:
                    value = cellset_as_dict['Cells'][ordinal_cells][cell_property]
                    content_as_dict[coordinates_sorted][cell_property] = value
                ordinal_axe0 += 1
                ordinal_cells += 1
                if top is not None and ordinal_cells >= top:
                    break
            if top is not None and ordinal_cells >= top:
                break
            ordinal_axe1 += 1
        return content_as_dict

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
    ''' Abstraction of the TM1 Subset (dynamic and static)

        :Notes:
            Done and tested. unittests available.
    '''
    def __init__(self, dimension_name, subset_name, alias, expression=None, elements=None):
        '''

        :param dimension_name: String
        :param subset_name: String
        :param alias: String, alias that is on in this subset.
        :param expression: String
        :param elements: List, element names
        '''
        self._dimension_name = dimension_name
        self._subset_name = subset_name
        self._alias = alias
        self._expression = expression
        self._elements = elements

    @property
    def dimension_name(self):
        return self._dimension_name

    @dimension_name.setter
    def dimension_name(self, value):
        self._dimension_name = value

    @property
    def name(self):
        return self._subset_name

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, value):
        self._alias = value

    @property
    def expression(self):
        return self._expression

    @expression.setter
    def expression(self, value):
        self._expression = value

    @property
    def elements(self):
        return self._elements

    @elements.setter
    def elements(self, value):
        self._elements = value

    @property
    def type(self):
        if self.expression:
            return 'dynamic'
        return 'static'

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
                   alias=subset_as_dict['Alias'],
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



    def add_elements(self, elements):
        ''' add Elements to static subsets
            :Parameters:
                `elements` : list of element names
        '''
        self._elements = self._elements + elements
        pass

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self._dimension_name)
        body_as_dict['Expression'] = self._expression
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._subset_name
        body_as_dict['Alias'] = self._alias
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self._dimension_name)
        body_as_dict['Elements@odata.bind'] = ['Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements(\'{}\')'
             .format(self.dimension_name, self.dimension_name, element) for element in self.elements]
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class AnnonymousSubset(Subset):
    ''' Abstraction of unregistered Subsets used in NativeViews (Check TM1py.ViewAxisSelection)

    '''
    def __init__(self, dimension_name, expression=None, elements=None):
        Subset.__init__(self, dimension_name=dimension_name, subset_name='', alias='', expression=expression, elements=elements)

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
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')'\
            .format(self._dimension_name, self._dimension_name)
        body_as_dict['Expression'] = self._expression
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Hierarchy@odata.bind'] = 'Dimensions(\'{}\')/Hierarchies(\'{}\')' \
            .format(self._dimension_name, self._dimension_name)
        body_as_dict['Elements@odata.bind'] = ['Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements(\'{}\')'
           .format(self.dimension_name, self.dimension_name, element) for element in self.elements]
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class View:
    ''' Abstraction of TM1 View
        serves as a parentclass for TM1py.MDXView and TM1py.NativeView

    '''
    def __init__(self, cube, name):
        self._cube = cube
        self._name = name

    @property
    def cube(self):
        return self._cube

    @property
    def name(self):
        return self._name

    @cube.setter
    def cube(self, value):
        self._cube = value

    @name.setter
    def name(self, value):
        self._name = value

class MDXView(View):
    ''' Abstraction on TM1 MDX view

        :usecase:
            user defines view with this class and creates it on TM1 Server.
            user calls get_view_data_structured from TM1pyQueries function to retrieve data from View

        :Notes:
            Complete, functional and tested.
            IMPORTANT. MDXViews cant be seen through the old TM1 clients (Archict, Perspectives). They do exist though!
    '''
    def __init__(self, cube_name, view_name, MDX):
        View.__init__(self, cube_name, view_name)
        self._MDX = MDX

    @property
    def MDX(self):
        return self._MDX

    @MDX.setter
    def MDX(self, value):
        self._MDX = value

    @property
    def body(self):
        return self.construct_body()

    @classmethod
    def from_json(cls, view_as_json, cube_name=None):
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict)

    @classmethod
    def from_dict(cls, view_as_dict, cube_name=None):
        return cls(cube_name=view_as_dict['Cube']['Name'] if not cube_name else cube_name,
                   view_name=view_as_dict['Name'],
                   MDX=view_as_dict['MDX'])

    def construct_body(self):
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._MDX
        return json.dumps(mdx_view_as_dict, ensure_ascii=False, sort_keys=False)

class NativeView(View):
    ''' Abstraction of TM1 NativeView (classic cube view)

        :Notes:
            Complete, functional and tested
    '''
    def __init__(self,
                 cube_name,
                 view_name,
                 suppress_empty_columns=False,
                 suppress_empty_rows=False,
                 format_string="0.#########\fG|0|",
                 titles = None,
                 columns = None,
                 rows = None):
        View.__init__(self, cube_name, view_name)
        self._suppress_empty_columns = suppress_empty_columns
        self._suppress_empty_rows = suppress_empty_rows
        self._format_string = format_string
        self._titles = titles if titles else []
        self._columns = columns if columns else []
        self._rows = rows if rows else []

    @property
    def body(self):
        return self._construct_body()

    @property
    def MDX(self):
        return self.as_MDX

    @property
    def as_MDX(self):
        # create the MDX Query
        mdx = 'SELECT '
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
                    if j == 0:
                        if self.suppress_empty_rows:
                            mdx += 'NON EMPTY '
                        mdx += subset._expression
                    else:
                        mdx += '*' + subset._expression
                else:
                    elements_as_unique_names = ['[' + axis_selection._dimension_name + '].[' + elem + ']' for elem in
                                                subset._elements]
                    mdx_subset = '{' + ','.join(elements_as_unique_names) + '}'
                    if j == 0:
                        if self.suppress_empty_columns:
                            mdx += 'NON EMPTY '
                        mdx += mdx_subset
                    else:
                        mdx += '*' + mdx_subset
            if i == 0:
                if len(self._rows) > 0:
                    mdx += ' on {}, '.format('ROWS')
            else:
                mdx += ' on {} '.format('COLUMNS')

        # append the FROM statement
        mdx += ' FROM [' + self._cube + '] '

        # itarate through titles - append the WHERE statement
        if len(self._titles) > 0:
            unique_names = []
            for title_selection in self._titles:
                dimension_name = title_selection._dimension_name
                selection = title_selection._selected
                unique_names.append('[' + dimension_name + '].[' + selection + ']')
            mdx += 'WHERE (' + ','.join(unique_names) + ') '

        return mdx

    @property
    def suppress_empty_cells(self):
        return self._suppress_empty_columns and self._suppress_empty_rows

    @property
    def suppress_empty_columns(self):
        return self._suppress_empty_columns

    @property
    def suppress_empty_rows(self):
        return self._suppress_empty_rows

    @property
    def format_string(self):
        return self._format_string

    @suppress_empty_cells.setter
    def suppress_empty_cells(self, value):
        self.suppress_empty_columns = value
        self.suppress_empty_rows = value

    @suppress_empty_rows.setter
    def suppress_empty_rows(self, value):
        self._suppress_empty_rows = value

    @suppress_empty_columns.setter
    def suppress_empty_columns(self, value):
        self._suppress_empty_columns = value

    @format_string.setter
    def format_string(self, value):
        self._format_string = value

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

    @classmethod
    def from_json(cls, view_as_json, cube_name=None):
        ''' Alternative constructor
                :Parameters:
                    `view_as_json` : string, JSON

                :Returns:
                    `View` : an instance of this class
        '''
        view_as_dict = json.loads(view_as_json)
        return NativeView.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict, cube_name=None):
        titles, columns, rows = [], [], []

        for selection in view_as_dict['Titles']:
            if selection['Subset']['Name'] == '':
                subset = AnnonymousSubset.from_dict(selection['Subset'])
            else:
                subset = Subset.from_dict(selection['Subset'])
            selected = selection['Selected']['Name']
            titles.append(ViewTitleSelection(dimension_name=subset.dimension_name,
                                             subset=subset, selected=selected))
        for i, axe in enumerate([view_as_dict['Columns'], view_as_dict['Rows']]):
            for selection in axe:
                if selection['Subset']['Name'] == '':
                    subset = AnnonymousSubset.from_dict(selection['Subset'])
                else:
                    subset = Subset.from_dict(selection['Subset'])
                axis_selection = ViewAxisSelection(dimension_name=subset.dimension_name,
                                                   subset=subset)
                columns.append(axis_selection) if i == 0 else rows.append(axis_selection)

        return cls(cube_name = view_as_dict["@odata.context"][20:view_as_dict["@odata.context"].find("')/")] if not cube_name else cube_name,
                   view_name = view_as_dict['Name'],
                   suppress_empty_columns = view_as_dict['SuppressEmptyColumns'],
                   suppress_empty_rows = view_as_dict['SuppressEmptyRows'],
                   format_string = view_as_dict['FormatString'],
                   titles = titles,
                   columns = columns,
                   rows = rows)

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
    ''' Describes what is selected in a dimension on an axis. Can be a Registered Subset or an Annonymous Subset

    '''
    def __init__(self, dimension_name, subset):
        '''
            :Parameters:
                `dimension_name` : String
                `subset` : Subset or AnnonymousSubset
        '''
        self._subset = subset
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the ViewAxisSelection entity.

        :return: string, the valid JSON
        '''
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset,AnnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            path = 'Dimensions(\'{}\')/Hierarchies(\'{}\')/Subsets(\'{}\')'.format(
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = path
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class ViewTitleSelection:
    ''' Describes what is selected in a dimension on the view title.
        Can be a Registered Subset or an Annonymous Subset

    '''
    def __init__(self, dimension_name, subset, selected):
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name
        self._subset = subset
        self._selected = selected

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        ''' construct the ODATA conform JSON represenation for the ViewTitleSelection entity.

        :return: string, the valid JSON
        '''
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            path = 'Dimensions(\'{}\')/Hierarchies(\'{}\')/Subsets(\'{}\')'.format(
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = path
        selected = 'Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements(\'{}\')'.format(
            self._dimension_name, self._hierarchy_name, self._selected)
        body_as_dict['Selected@odata.bind'] = selected
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class Dimension:
    ''' Abstraction of TM1 Dimension

        :Notes:
            Not complete. Not tested.
            A Dimension is a container for hierarchies.
    '''
    def __init__(self, name, hierarchies=None):
        '''
        :Parameters:
            - `name` : string
                the name of the dimension
        '''
        if hierarchies is None:
            hierarchies=[]
        self._name = name
        self._hierarchies = hierarchies
        self._attributes = {'Caption': name}

    @staticmethod
    def from_json(dimension_as_json):
        dimension_as_dict = json.loads(dimension_as_json)
        return Dimension.from_dict(dimension_as_dict)

    @staticmethod
    def from_dict(dimension_as_dict):
        return Dimension(name=dimension_as_dict['Name'],
                         hierarchies=[Hierarchy.from_dict(hierarchy) for hierarchy in dimension_as_dict['Hierarchies']])

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._construct_body()

    @property
    def unique_name(self):
        return '[' + self._name + ']'

    @property
    def hierarchies(self):
        return self._hierarchies

    @property
    def default_hierarchy(self):
        return self._hierarchies[0]

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def body(self):
        return json.dumps(self._construct_body(), ensure_ascii=False, sort_keys=False)

    @property
    def body_as_dict(self):
        return self._construct_body()

    def __iter__(self):
        return iter(self._hierarchies)

    def __len__(self):
        return len(self.hierarchies)

    def add_hierarchy(self, hierarchy):
        self._hierarchies.append(hierarchy)

    def remove_hierarchy(self, name):
        self._hierarchies = list(filter(lambda h: h.name != name, self._hierarchies))

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        #self.body_as_dict["@odata.type"] = "ibm.tm1.api.v1.Dimension"
        body_as_dict["Name"] = self._name
        body_as_dict["UniqueName"] = self.unique_name
        body_as_dict["Attributes"] = self._attributes
        body_as_dict["Hierarchies"] = [hierarchy.body_as_dict for hierarchy in self.hierarchies]
        return body_as_dict

class Hierarchy:
    ''' Abstraction of TM1 Hierarchy

        :Notes:

    '''

    def __init__(self, name, dimension_name, elements=None, element_attributes=None,
                 edges=None, subsets=None, default_member=None):
        self._name = name
        self._dimension_name = dimension_name
        self._elements = {elem.name: elem for elem in elements} if elements else {}
        self._element_attributes = element_attributes if element_attributes else []
        self._edges = edges if edges else []
        self._subsets = subsets if subsets else []
        self._default_member = default_member

    @staticmethod
    def from_dict(hierarchy_as_dict):
        return Hierarchy(name=hierarchy_as_dict['Name'],
                         dimension_name=hierarchy_as_dict['Dimension']['Name'],
                         elements=[Element.from_dict(elem) for elem in hierarchy_as_dict['Elements']],
                         element_attributes=[ElementAttribute(ea['Name'], ea['Type'])
                                             for ea in hierarchy_as_dict['ElementAttributes']],
                         edges=[Edge.from_dict(edge) for edge in hierarchy_as_dict['Edges']],
                         subsets=[subset['Name'] for subset in hierarchy_as_dict['Subsets']],
                         default_member=hierarchy_as_dict['DefaultMember']['Name'])

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def dimension_name(self):
        return self._dimension_name

    @property
    def elements(self):
        return self._elements

    @property
    def element_attributes(self):
        return self._element_attributes

    @property
    def edges(self):
        return self._edges

    @property
    def subsets(self):
        return self._subsets

    @property
    def default_member(self):
        return self._default_member

    @property
    def body(self):
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self):
        return self._construct_body()

    def add_element(self, element_name, element_type):
        if element_name.lower() in [elem.name.lower() for elem in self]:
            # elementname already used
            raise Exception("Elementname has to be unqiue")
        e = Element( name=element_name, element_type=element_type)
        self._elements[element_name] = e

    def update_element(self, element_name, element_type=None):
        self._elements[element_name].element_type = element_type

    def add_edge(self, edge):
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge(self, edge):
        self._edges = [e for e in self.edges if not e == edge]

    def _construct_body(self, element_attributes=False):
        """

        :param element_attributes: Only include element_attributes in body if explicitly asked for
        :return:
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name']=self._name
        body_as_dict['Elements']=[]
        body_as_dict['Edges'] = []

        for element in self._elements.values():
            body_as_dict['Elements'].append(element.body)
        for edge in self._edges:
            body_as_dict['Edges'].append(edge.body_as_dict)
        if element_attributes:
            body_as_dict['ElementAttributes'] = []
            for element_attribute in self._element_attributes:
                body_as_dict['ElementAttributes'].append(element_attribute)
        return body_as_dict

    def __iter__(self):
        return iter(self._elements.values())

    def __len__(self):
        return len(self._elements.values())

class Element:
    """ Abstraction of TM1 Element

    """
    valid_types = ['NUMERIC', 'STRING', 'CONSOLIDATED']
    def __init__(self, name, element_type, attributes= None, unique_name=None, index=None):
        self._name = name
        self._unique_name = unique_name
        self._index = index
        self._element_type = None
        self.element_type = element_type
        self._attributes = attributes

    @staticmethod
    def from_dict(element_as_dict):
        return Element(name=element_as_dict['Name'],
                       unique_name=element_as_dict['UniqueName'],
                       index=element_as_dict['Index'],
                       element_type=element_as_dict['Type'],
                       attributes=element_as_dict['Attributes'])

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def unique_name(self):
        return self._unique_name

    @property
    def index(self):
        return self._index

    @property
    def element_attributes(self):
        return self._attributes

    @property
    def element_type(self):
        return self._element_type

    @element_type.setter
    def element_type(self, value):
        if value.upper() in self.valid_types:
            self._element_type = value
        else:
            raise Exception('{} not a valid Element Type'.format(value))

    @property
    def body(self):
        return self._construct_body()

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._name
        body_as_dict['Type'] = self._element_type
        return body_as_dict

class Edge:
    """

    :Notes: Maybe obsolete. Edges could be stored in Hierarchy as dictioary of element names as key and weight as value

    """
    def __init__(self, parent_name, component_name, weight):
        self._parent_name = parent_name
        self._component_name = component_name
        self._weight = weight

    @staticmethod
    def from_dict(edge_as_dict):
        return Edge(parent_name=edge_as_dict['ParentName'],
                    component_name=edge_as_dict['ComponentName'],
                    weight=edge_as_dict['Weight'])

    @property
    def parent_name(self):
        return self._parent_name

    @property
    def component_name(self):
        return self._component_name

    def __eq__(self, other):
        return self.parent_name == other.parent_name and self.component_name == other.component_name

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def body(self):
        return json.dumps(self._construct_body(),ensure_ascii=False)

    @property
    def body_as_dict(self):
        return self._construct_body()

    def _construct_body(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['ParentName'] = self._parent_name
        body_as_dict['ComponentName'] = self._component_name
        return body_as_dict

class ElementAttribute:
    valid_types = ['NUMERIC', 'STRING', 'ALIAS']

    def __init__(self, name, attribute_type):
        self._name = None
        self.name = name
        self._attribute_type = None
        self.attribute_type = attribute_type

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def attribute_type(self):
        return self._attribute_type

    @attribute_type.setter
    def attribute_type(self, value):
        if value.upper() in self.valid_types:
            self._attribute_type = value
        else:
            raise Exception('{} not a valid Attribute Type.'.format(value))

    @property
    def body_as_dict(self):
        return {"Name": self._name, "Type": self._attribute_type}

    @property
    def body(self):
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @classmethod
    def from_json(cls, element_attribute_as_json):
        return cls.from_dict(json.loads(element_attribute_as_json))

    @classmethod
    def from_dict(cls, element_attribute_as_dict):
        return cls(name=element_attribute_as_dict['Name'],
                   attribute_type=element_attribute_as_dict['Type'])


class Annotation:
    ''' Abtraction of TM1 Annotation

        :Notes:
            - Class complete, functional and tested.
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

    @property
    def comment_value(self):
        return self._comment_value

    @comment_value.setter
    def comment_value(self, value):
        self._comment_value = value

    @property
    def id(self):
        return self._id

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
        commentLocations = ','.join(self._dimensional_context)
        body['commentLocation'] = commentLocations[1:]
        body['commentType'] = self._comment_type
        body['commentValue'] = self._comment_value
        body['objectName'] = self._object_name
        return json.dumps(body, ensure_ascii=False, sort_keys=False)

class Process:
    ''' abstraction of a TM1 Process.

        :Notes:
        - class complete, functional and tested !!
        - issues with password for processes with ODBC Datasource
        - doenst work with Processes that were generated through the Wizard
    '''

    ''' the auto_generated_string code is required to be in all code-tabs. '''
    auto_generated_string = "#****Begin: Generated Statements***\r\n#****End: Generated Statements****\r\n"

    def __init__(self, name, has_security_access=False, ui_data="CubeAction=1511€DataAction=1503€CubeLogChanges=0€",
                 parameters=None, variables=None, variables_ui_data=None, prolog_procedure='', metadata_procedure='',
                 data_procedure='', epilog_procedure= '', datasource_type='None', datasource_ascii_decimal_separator='.',
                 datasource_ascii_delimiter_char=';', datasource_ascii_delimiter_type='Character',
                 datasource_ascii_header_records=1, datasource_ascii_quote_character='', datasource_ascii_thousand_separator=',',
                 datasource_data_source_name_for_client='', datasource_data_source_name_for_server='', datasource_password='',
                 datasource_user_name='', datasource_query='', datasource_uses_unicode=True, datasource_view='',
                 datasource_subset=''):
        ''' Default construcor

        :param name: name of the process - mandatory
        :param others: all other parameters optional
        :return:
        '''
        self.name = name
        self.has_security_access = has_security_access
        self.ui_data = ui_data
        self.parameters = []
        self.parameters = parameters if parameters else []
        self.variables = variables if variables else []
        self.variables_ui_data = variables_ui_data if variables_ui_data else []
        add_generated_string = lambda code: self.auto_generated_string + code \
            if self.auto_generated_string not in code else code
        self.prolog_procedure = add_generated_string(prolog_procedure)
        self.metadata_procedure = add_generated_string(metadata_procedure)
        self.data_procedure = add_generated_string(data_procedure)
        self.epilog_procedure = add_generated_string(epilog_procedure)
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
        self.datasource_subset = datasource_subset

    @classmethod
    def from_json(cls, process_as_json):
        """

        :param process_as_json: response of /api/v1/Processes('x')?$expand=*
        :return: an instance of this class
        """

        process_as_dict = json.loads(process_as_json)
        return cls.from_dict(process_as_dict)

    @classmethod
    def from_dict(cls, process_as_dict):
        """

        :param process_as_json: Dictionary, process as dictionary
        :return: an instance of this class
        """
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
                   datasource_view=f(process_as_dict['DataSource'], 'view'),
                   datasource_subset=f(process_as_dict['DataSource'], 'subset'))

    @property
    def body(self):
        return self._construct_body()

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
        # '\r' !
        variable_ui_data = 'VarType=' +  str(var_type) + '\r' + 'ColType=' + str(827)+ '\r'
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
        self.prolog_procedure = self.auto_generated_string + prolog_procedure \
            if self.auto_generated_string not in prolog_procedure else prolog_procedure

    def set_metadata_procedure(self, metadata_procedure):
        self.metadata_procedure =self.auto_generated_string + metadata_procedure \
            if self.auto_generated_string not in metadata_procedure else metadata_procedure

    def set_data_procedure(self, data_procedure):
        self.data_procedure = self.auto_generated_string +  data_procedure \
            if self.auto_generated_string not in data_procedure else data_procedure

    def set_epilog_procedure(self, epilog_procedure):
        self.epilog_procedure = self.auto_generated_string + epilog_procedure \
            if self.auto_generated_string not in epilog_procedure else epilog_procedure

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

    def set_datasource_subset(self, datasource_subset):
        self.datasource_subset = datasource_subset

    #construct self.body (json) from the class-attributes
    def _construct_body(self):
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

        elif self.datasource_type == 'TM1DimensionSubset':
            body_as_dict['DataSource'] = {
                "Type": self.datasource_type,
                "dataSourceNameForClient": self.datasource_data_source_name_for_server,
                "dataSourceNameForServer": self.datasource_data_source_name_for_server,
                "subset": self.datasource_subset
            }
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

class ChoreTask:
    def __init__(self, step, process_name, parameters):
        self._step = step
        self._process_name = process_name
        self._parameters = parameters

    @classmethod
    def from_dict(cls, chore_task_as_dict):
        return cls(step = int(chore_task_as_dict['Step']),
                   process_name = chore_task_as_dict['Process']['Name'],
                   parameters = [{'Name':p['Name'],'Value':p['Value']} for p in chore_task_as_dict['Parameters']])

    @property
    def body(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['Process@odata.bind'] = 'Processes(\'{}\')'.format(self._process_name)
        body_as_dict['Parameters'] = self._parameters
        return body_as_dict

    def __eq__(self, other):
        return self._process_name == other._process_name and self._parameters == other._parameters

    def __ne__(self, other):
        return self._process_name != other._process_name or self._parameters != other._parameters

class ChoreStartTime:
    '''
    GMT Time!
    '''
    def __init__(self, year, month, day, hour, minute, second):
        self._datetime = datetime.combine(date(year, month, day), time(hour, minute, second))


    @classmethod
    def from_string(cls, start_time_string):
        # f to handle strange timestamp 2016-09-25T20:25Z instead of common 2016-09-25T20:25:01Z
        f = lambda x: int(x) if x else 0
        return cls(year=f(start_time_string[0:4]),
                   month=f(start_time_string[5:7]),
                   day=f(start_time_string[8:10]),
                   hour=f(start_time_string[11:13]),
                   minute=f(start_time_string[14:16]),
                   second=f(start_time_string[17:19]))

    @property
    def start_time_string(self):
        return self._datetime.strftime( "%Y-%m-%dT%H:%M:%SZ")

    def __str__(self):
        return self._datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    def set_time(self, year=None, month=None, day=None, hour=None, minute=None, second=None):
        if year:
            self._datetime = self._datetime.replace(year=year)
        if month:
            self._datetime = self._datetime.replace(month=month)
        if day:
            self._datetime = self._datetime.replace(day=day)
        if hour:
            self._datetime = self._datetime.replace(hour=hour)
        if minute:
            self._datetime = self._datetime.replace(minute=minute)
        if second:
            self._datetime = self._datetime.replace(second=second)

    def add(self,days=0, hours=0, minutes=0, seconds=0):
        self._datetime = self._datetime + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def substract(self,days=0, hours=0, minutes=0, seconds=0):
        self._datetime = self._datetime - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

class ChoreFrequency:
    def __init__(self, days, hours, minutes, seconds):
        self._days = str(days).zfill(2)
        self._hours = str(hours).zfill(2)
        self._minutes = str(minutes).zfill(2)
        self._seconds = str(seconds).zfill(2)

    @property
    def days(self):
        return self._days

    @property
    def hours(self):
        return self._hours

    @property
    def minutes(self):
        return self._minutes

    @property
    def seconds(self):
        return self._seconds

    @days.setter
    def days(self, value):
        self._days = str(value).zfill(2)

    @hours.setter
    def hours(self, value):
        self._hours = str(value).zfill(2)

    @minutes.setter
    def minutes(self, value):
        self._minutes = str(value).zfill(2)

    @seconds.setter
    def seconds(self, value):
        self._seconds = str(value).zfill(2)

    @classmethod
    def from_string(cls, frequency_string):
        pos_dt = frequency_string.find('DT',1)
        pos_h = frequency_string.find('H',pos_dt)
        pos_m = frequency_string.find('M',pos_h)
        pos_s = len(frequency_string)-1
        return cls(days=frequency_string[1:pos_dt],
                   hours=frequency_string[pos_dt+2:pos_h],
                   minutes=frequency_string[pos_h+1:pos_m],
                   seconds=frequency_string[pos_m+1:pos_s])

    @property
    def frequency_string(self):
        return "P{}DT{}H{}M{}S".format(self._days, self._hours, self._minutes, self._seconds)

    def __str__(self):
        return "P{}DT{}H{}M{}S".format(self._days, self._hours, self._minutes, self._seconds)

class Chore:
    def __init__(self, name, start_time, dst_sensitivity, active, execution_mode, frequency, tasks):
        self._name = name
        self._start_time = start_time
        self._dst_sensitivity = dst_sensitivity
        self._active = active
        self._execution_mode = execution_mode
        self._frequency = frequency
        self._tasks = tasks

    @classmethod
    def from_json(cls, chore_as_json):
        ''' Alternative constructor

        :param chore_as_json: string, JSON. Response of /api/v1/Chores('x')/Tasks?$expand=*
        :return: Chore, an instance of this class
        '''
        chore_as_dict = json.loads(chore_as_json)
        return cls.from_dict(chore_as_dict)

    @classmethod
    def from_dict(cls, chore_as_dict):
        ''' Alternative constructor

        :param chore_as_dict: Chore as dict
        :return: Chore, an instance of this class
        '''
        return cls(name=chore_as_dict['Name'],
                   start_time= ChoreStartTime.from_string(chore_as_dict['StartTime']),
                   dst_sensitivity = chore_as_dict['DSTSensitive'],
                   active = chore_as_dict['Active'],
                   execution_mode = chore_as_dict['ExecutionMode'],
                   frequency = ChoreFrequency.from_string(chore_as_dict['Frequency']),
                   tasks = [ChoreTask.from_dict(task) for task in chore_as_dict['Tasks']])

    def add_task(self, task):
        self._tasks.append(task)

    def activate(self):
        self._active = True

    def deactivate(self):
        self._active = False

    def reschedule(self, days=0, hours=0, minutes=0, seconds=0):
        self._start_time.add(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @property
    def body(self):
        return self.construct_body()

    def construct_body(self):
        '''
        construct self.body (json) from the class attributes
        :return: String, TM1 JSON representation of a chore
        '''
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self._name
        body_as_dict['StartTime'] = self._start_time.start_time_string
        body_as_dict['DSTSensitive'] = self._dst_sensitivity
        body_as_dict['Active'] = self._active
        body_as_dict['ExecutionMode'] = self._execution_mode
        body_as_dict['Frequency'] = self._frequency.frequency_string
        body_as_dict['Tasks'] = [task.body for task in self._tasks]
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)


class User:
    def __init__(self, name, groups, friendly_name=None, password=None):
        self._name = name
        self._groups = [group for group in groups]
        self._friendly_name = friendly_name
        self._password = password

    @property
    def name(self):
        return self._name

    @property
    def friendly_name(self):
        return self._friendly_name

    @property
    def password(self):
        if self._password:
            return b64encode(str.encode(self._password))

    @property
    def is_admin(self):
        return 'ADMIN' in self.groups

    @property
    def groups(self):
        return [group for group in self._groups]

    @name.setter
    def name(self, value):
        self._name = value

    @friendly_name.setter
    def friendly_name(self, value):
        self._friendly_name = value

    @password.setter
    def password(self, value):
        self._password = value

    def add_group(self, group_name):
        if group_name.upper() not in [group.upper() for group in self._groups]:
            self._groups.append(group_name)

    def remove_group(self, group_name):
        try:
            index = [group.upper() for group in self._groups].index(group_name.upper())
            self._groups.pop(index)
        except ValueError:
            pass

    @classmethod
    def from_json(cls, user_as_json):
        ''' Alternative constructor

        :param user_as_json: user as JSON string
        :return: user, an instance of this class
        '''
        user_as_dict = json.loads(user_as_json)
        return cls.from_dict(user_as_dict)

    @classmethod
    def from_dict(cls, user_as_dict):
        ''' Alternative constructor

        :param user_as_dict: user as dict
        :return: user, an instance of this class
        '''
        return cls(name=user_as_dict['Name'],
                   friendly_name=user_as_dict['FriendlyName'],
                   groups=[group['Name'].upper() for group in user_as_dict['Groups']])

    @property
    def body(self):
        return self.construct_body()

    def construct_body(self):
        '''
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a user
        '''
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self.name
        body_as_dict['FriendlyName'] = self.friendly_name
        if self.password:
            body_as_dict['Password'] = self._password
        body_as_dict['Groups@odata.bind'] = ['Groups(\'{}\')'.format(group) for group in self.groups]
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=True)

class Cube:
    def __init__(self, name, dimensions, rules=None):
        self._name = name
        self._dimensions = dimensions
        self._rules = rules

    @property
    def name(self):
        return self._name
    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value):
        self._dimensions = value

    @property
    def has_rules(self):
        if self._rules:
            return True
        return False

    @property
    def rules(self):
        return self._rules

    @rules.setter
    def rules(self, value):
        self._rules = value


    @property
    def skipcheck(self):
        if self.has_rules:
            return self.rules.skipcheck
        return False

    @property
    def undefvals(self):
        if self.has_rules:
            return self.rules.undefvals
        return False

    @property
    def feedstrings(self):
        if self.has_rules:
            return self.rules.feedstrings
        return False

    @classmethod
    def from_json(cls, cube_as_json):
        ''' Alternative constructor

        :param cube_as_json: user as JSON string
        :return: cube, an instance of this class
        '''
        cube_as_dict = json.loads(cube_as_json)
        return cls.from_dict(cube_as_dict)

    @classmethod
    def from_dict(cls, cube_as_dict):
        ''' Alternative constructor

        :param cube_as_dict: user as dict
        :return: user, an instance of this class
        '''
        return cls(name=cube_as_dict['Name'],
                   dimensions=[dimension['Name'] for dimension in cube_as_dict['Dimensions']],
                   rules=Rules(cube_as_dict['Rules']) if cube_as_dict['Rules'] else None)

    @property
    def body(self):
        return self.construct_body()

    def construct_body(self):
        '''
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a cube
        '''
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self.name
        body_as_dict['Dimensions@odata.bind'] = ['Dimensions(\'{}\')'.format(dimension) for dimension in self.dimensions]
        if self.rules:
            body_as_dict['Rules'] = str(self.rules)
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=True)

class Rules:
    """
        Abstraction of Rules on a cube.

        rules_analytics
        is a collection of rulestatements, where each statement is without linebreaks.
        comments are not included.

        Currently rules object not meant not be edited. To be written!

    """
    keywords = ['SKIPCHECK', 'FEEDSTRINGS', 'UNDEFVALS', 'FEEDERS']

    def __init__(self, rules):
        self._text = rules
        self._rules_analytics = []
        self._rules_analytics_upper = []
        self.init_analytics()

    def init_analytics(self):
        text_without_comments = '\n'.join(
            [rule for rule in self._text.split('\n') if len(rule) > 0 and rule.strip()[0] != '#'])
        for statement in text_without_comments.split(';'):
            if len(statement.strip()) > 0:
                self._rules_analytics.append(statement.replace('\n', ''))
        # self._rules_analytics_upper serves for analysis on cube rules
        self._rules_analytics_upper = [rule.upper() for rule in self._rules_analytics]

    @property
    def text(self):
        return self._text

    @property
    def rules_analytics(self):
        return self._rules_analytics

    @property
    def rule_statements(self):
        if self.has_feeders:
            return self.rules_analytics[:self._rules_analytics_upper.index('FEEDERS')]
        return self.rules_analytics

    @property
    def feeder_statements(self):
        if self.has_feeders:
            return self.rules_analytics[self._rules_analytics_upper.index('FEEDERS')+1:]
        return []

    @property
    def skipcheck(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'SKIPCHECK':
                return True
        return False

    @property
    def undefvals(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'UNDEFVALS':
                return True
        return False

    @property
    def feedstrings(self):
        for rule in self._rules_analytics_upper[0:5]:
            if rule == 'FEEDSTRINGS':
                return True
        return False

    @property
    def has_feeders(self):
        if 'FEEDERS' in self._rules_analytics_upper:
            # has feeders declaration
            feeders = self.rules_analytics[self._rules_analytics_upper.index('FEEDERS'):]
            # has more at least one actual feeder statements
            return len(feeders) > 1
        return False

    def __len__(self):
        return len(self.rules_analytics)

    # iterate through actual rule statments without linebreaks. Ignore comments.
    def __iter__(self):
        return iter(self.rules_analytics)

    def __str__(self):
        return self.text
