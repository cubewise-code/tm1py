__author__ = 'OLAPLINE, Marius'

import requests
import json
import collections
import http.client

class pyTM1Exception(Exception):
    pass


class httpClientTM1:
    ''' low level communication with TM1 server via http

    '''
    def __init__(self, address, port, user, password, ssl):
        '''Create an instance of httpClientTM1

        :Parameters:
            `address`: String
                the IP address of the TM1 Server
            `port`: Int
                httpPortNumber as specified in the tm1s.cfg
            `user`: String
                the TM1 user
            `password` : String
                the password for the given TM1 user
            ´ssl´ : boolean
                as specified in the tm1s.cfg
        '''
        self._address = 'localhost' if address == '' else address
        self._port = port
        self._user = user
        self._password = password
        self._ssl = ssl
        self._auth = (self._user,self._password)
        self._cookies = None
        self._s = requests.session()
        self._headers= {'connection': 'keep-alive', 'cache': 'no-cache', 'user-agent': 'TM1py',
                       'content-type': 'application/json; odata.metadata=minimal; odata.streaming=true; charset=utf-8'}
        requests.packages.urllib3.disable_warnings()
        self._get_cookies()

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
        r = self._s.get(url=url,headers=self._headers, auth=self._auth, data=data, cookies=self._cookies,
                       verify=False)
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
        r = self._s.post(url=url,headers=self._headers, auth=self._auth, data=data, cookies=self._cookies,
                        verify=False)
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
        r = self._s.patch(url=url,headers=self._headers, auth=self._auth, data=data, cookies=self._cookies,
                         verify=False)
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
        r = self._s.delete(url=url,headers=self._headers, auth=self._auth, data=data, cookies=self._cookies,
                          verify=False)
        self._varify_response(response=r)
        return r.text

    def _get_cookies(self):
        ''' perform a simple GET request: Ask for the TM1 Version
            Store cookie that comes with the response
        '''
        if self._ssl:
            url = 'https://' + self._address + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        else:
            url = 'http://' + self._address + ':' + str(self._port) + '/api/v1/Configuration/ProductVersion'
        r = self._s.get(url=url,headers=self._headers, auth=self._auth, data='', cookies=self._cookies,
                       verify=False)
        self._cookies = r.cookies

    def _url_and_body(self, request, data):
        ''' create proper url and payload

            :Notes:
                - perhaps more characters should be replaced in url.
        '''
        if self._ssl:
             url = 'https://' + self._address + ':' + str(self._port) + request
        else:
             url = 'http://' + self._address + ':' + str(self._port) + request
        url = url.replace(' ', '%20').replace('#','%23')
        data = data.encode('utf-8')
        return url, data

    def _varify_response(self, response):
        ''' check if Status Code is OK

        :Parameters:
            `response`: String
                the response that is returned from a method call

        :Exceptions:
            pyTM1Exception, raises pyTM1Exception when Code is in between 400 and 600
        '''
        if not response.ok:
            raise pyTM1Exception('Status_code: {} Message: {}'.format(response.status_code, response.json()['error']['message']))


# offers predefined Queries for interaction with TM1 Server
class TM1Queries:
    ''' Class offers predefined CRUD (Create, Read, Update, Delete) functions to interact with a TM1 Server

    Create method - `create` prefix
    Read methods - `get` prefix
    Update methods - `update prefix`
    Delete methods - `delete prefix`

    '''

    def __init__(self, ip, port, user, password, ssl):
        '''Create an instance of TM1Qeueries

        :Parameters:
            `address`: String
                the IP address of the TM1 Server
            `port`: Int
                httpPortNumber as specified in the tm1s.cfg
            ´user´: String
                the TM1 user
            ´password´ : String
                the password for the given TM1 user
            ´ssl´ : boolean
                as specified in the tm1s.cfg

        '''
        self._ip = ip
        self._port = port
        self._user = user
        self._password = password
        self._ssl = ssl

        self._client = httpClientTM1(ip, port, user, password, ssl)

    @staticmethod
    def get_all_servers_from_adminhost(adminhost = 'localhost'):
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
        ''' End TM1 Session and http session

        '''
        self._client.GET('/api/logout','')

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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_server_name()

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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_all_dimension_names()

    def execute_given_process(self, name_process):
        ''' Ask TM1 Server to execute a process

        :Parameters:
            `name_process`: String
                name of the process to be executed

        :Returns:
            Boolean, indictes succes or fail or execution
            String, the response

        Note : parameters missing !!
        '''
        try:
            response = self._client.POST("/api/v1/Processes('" + name_process +"')/tm1.Execute", "")
            return not "error" in response, response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.execute_given_process(name_process)

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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_all_process_names()

    def get_process(self, name_process):
        ''' Get a process from TM1 Server

        :Parameters:
            `name_process`: String

        :Returns:
             Instance of the Process class
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
            response = self._client.GET(request,"")
            return Process.from_json(process_as_json=response)
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_process_as_dict(name_process)

    def get_process_as_dict(self, name_process):
        ''' Get a process from TM1 Server in a dictionary
        dictionary contains properties and navigation properties

        :Parameters:
            `name_process`: String

        :Returns:
            dictionary, the process
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
                                                          "DataSource/view"
            response = self._client.GET(request,"")
            dict_process = json.loads(response)
            return dict_process
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_process_as_dict(name_process)

    def update_process(self, process):
        ''' update an existing Process on TM1 Server

        :Parameters:
            `process`: Instance of TM1py.Process class

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Processes('" + process.name + "')"
            response = self._client.PATCH(request,process.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.update_process(process)

    # temporary function !
    def save_process(self, process):
        return self.update_process(process)

    def create_process(self, process):
        ''' post a new process against TM1 Server

        :Parameters:
            `process`: Instance of Process class

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Processes"
            response = self._client.POST(request, process.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.create_process(process)

    def create_view(self, view):
        ''' create a new view on TM1 Server

        :Parameters:
            `view`: instance of subclass of TM1.View (NativeView or MDXView)

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Cubes('" + view._cube + "')/Views"
            response = self._client.POST(request, view.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.create_view(view)

    def get_native_view(self, name_cube, name_view):
        view_as_json = self._client.GET("/api/v1/Cubes('{}')/Views('{}')".format(name_cube, name_view))
        titles_as_json = self._client.GET("/api/v1/Cubes('{}')/Views('{}')/Titles?$expand=*".format(name_cube, name_view))
        columns_as_json = self._client.GET("/api/v1/Cubes('{}')/Views('{}')/Columns?$expand=*".format(name_cube, name_view))
        rows_as_json = self._client.GET("/api/v1/Cubes('{}')/Views('{}')/Rows?$expand=*".format(name_cube, name_view))
        native_view = NativeView.from_json(view_as_json, titles_as_json, columns_as_json, rows_as_json)
        return native_view

    def update_native_view(self, native_view):
        ''' update a native view on TM1 Server

        :Parameters:
            `view`: instance of subclass of NativeView

        :Returns:
            `string` : the response
        '''
        try:
            request = "/api/v1/Cubes({})/Views({})".format(native_view.get_cube, native_view.get_name)
            response = self._client.PATCH(request, native_view.body)
            return response
        except:
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.update_native_view(native_view)

    def update_view(self, view):
        if type(view) == 'MDXView':
            self._update_mdx_view(view)
        elif type(view) == NativeView:
            self._update_native_view(view)
        else:
            raise pyTM1Exception('given view is not of type MDXView or NativeView')


    def _update_mdx_view(self, view):
        pass

    def _update_native_view(self, view):
        pass

    def delete_view(self, name_cube, name_view):
        try:
            request = "/api/v1/Cubes('{}')/Views('{}')".format(name_cube, name_view)
            response = self._client.DELETE(request)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.delete_view(view)

    def get_all_annotations_from_cube(self, name_cube):
        ''' Get all annotations from given cube as a List.

        :Parameters:
            `name_cube`: name of the cube

        :Returns:
            `List` : list of instances of TM1py.Annotation
        '''
        try:
            request = "/api/v1/Cubes('{}')/Annotations?$expand=DimensionalContext($select=Name)".format(name_cube)
            response = self._client.GET(request,'')
            annotations_as_dict = json.loads(response)['value']
            annotations = [Annotation.from_json(json.dumps(element)) for element in annotations_as_dict]
            return annotations
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_cube_names_and_dimensions()

    def _get_view_content_native(self,name_cube, name_view, top=None):
        ''' Get view content as dictionary in its native structure.

        :Parameters:
            `name_cube` : String
            `name_view` : String
            `top` : Int, number of cells

        :Returns:
            `Dictionary` : {Cells : {}, 'ID' : '', 'Axes' : [{'Ordinal' : 1, Members: [], ...},
            {'Ordinal' : 2, Members: [], ...}, {'Ordinal' : 3, Members: [], ...} ] }
        '''
        if top is not None:
            request = '/api/v1/Cubes(\'' + name_cube + '\')/Views(\'' + name_view + \
                      '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members($select=UniqueName);$top='\
                      + str(top)+')),Cells($select=Value,Ordinal;$top=' + str(top) + ')'
        else:
            request = '/api/v1/Cubes(\'' + name_cube + '\')/Views(\'' + name_view + \
                      '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members($select=UniqueName))),' \
                      'Cells($select=Value,Ordinal)'

        response = self._client.POST(request, '')
        return json.loads(response)

    def get_view_content_structured(self, cube_name, view_name, top=None):
        ''' Get view content as dictionary with sweet and concise structure

        :Parameters:
            `name_cube` : String
            `name_view` : String
            `top` : Int, number of cells

        :Returns:
            `Dictionary` : {([dim1].[elem1], [dim2][elem1]): 3127.312, ....  }
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
            ordinal_axe0 = 0
            #get coordinates on axe 1: Rows
            Tuples_as_dict = axe1_as_dict['Tuples'][ordinal_axe1]['Members']
            elements_on_axe1 = [data['UniqueName'] for data in Tuples_as_dict]

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


    # replaced by "get_view_content_structured"
    # get content of given view in dictionary {(elem1, elem2, elem3) : {Value: 189.12, RuleDerived: True, .... }, ....}
    # only works with views that have all the dimensions as rows !
    def get_view_content_as_dict_old(self, cube_name, view_name, all=True, Status=False, FormatString=False,
                                 FormattedValue= False, Updateable=False, RuleDerived=False, Annotated=False,
                                 Consolidated=False, Language=False, HasPicklist=False, PicklistValues=False):
        try:
            # replace spaces with '%20' for http. has to be down one layer deeper !
            cube_name = cube_name.replace(' ','%20')
            view_name = view_name.replace(' ','%20')
            succes, dimension_order = self.get_dimension_order(cube_name)
            view = {}
            if all is True:
                request = '/api/v1/Cubes(\'' + cube_name + '\')/Views(\'' + view_name + \
                          '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members)),' \
                          'Cells($select=Value,Ordinal,Status,Value,FormatString,FormattedValue,' \
                          'Updateable,RuleDerived,Annotated,Consolidated,Language,HasPicklist,PicklistValues)'
            else:
                all_cell_attributes = ['Status','FormatString','FormattedValue','Updateable','RuleDerived','Annotated',
                                       'Consolidated','Language','HasPicklist','PicklistValues']
                booleans = [Status, FormatString, FormattedValue, Updateable, RuleDerived, Annotated,
                            Consolidated, Language, HasPicklist, PicklistValues]
                selected_cell_attributes = [attribute for attribute, bool in zip(all_cell_attributes, booleans) if bool]
                request = '/api/v1/Cubes(\'' + cube_name + '\')/Views(\'' + view_name + \
                          '\')/tm1.Execute?$expand=Axes($expand=Tuples($expand=Members)),Cells($select=Value,Ordinal'
                if len(selected_cell_attributes) > 0:
                    request += ',' + ','.join(selected_cell_attributes) + ')'
                else:
                    request += ')'

            #print(request)

            response = self._client.POST(request, '')
            resp_as_dict = json.loads(response)

            y_axis = resp_as_dict['Axes'][1]['Tuples']
            for i in range(0, len(resp_as_dict['Cells'])):
                elements = list(block['UniqueName'] for block in y_axis[i]['Members'])
                if len(elements) > 0:
                    elements_sorted = self.sort_addresstuple(cube_name, elements, dimension_order)
                    cell = resp_as_dict['Cells'][i]
                    view[tuple(elements_sorted)] = cell
            return not 'error' in response, view
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_view_content_as_dict(cube_name, view_name, all=True, Status=False, FormatString=False,
                                          FormattedValue= False, Updateable=False, RuleDerived=False, Annotated=False,
                                          Consolidated=False, Language=False, HasPicklist=False, PicklistValues=False)

    def get_dimension_order(self, name_cube):
        ''' Get the order of dimensions in a cube

        :Parameters:
            `name_cube` : String

        :Returns:
            `List` : [dim1, dim2, dim3, etc.]
        '''
        try:
            response = self._client.GET('/api/v1/Cubes(\'' + name_cube + '\')/Dimensions?$select=Name', '')
            response_as_dict = json.loads(response)['value']
            dimension_order = [element['Name'] for element in response_as_dict]
            return dimension_order
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_dimension_order(name_cube)

    def sort_addresstuple(self, cube_name, dimension_order, unsorted_addresstuple):
        ''' Sort the given mixed up addresstuple

        :Parameters:
            `cube_name` : String
            `dimension_order` : list of dimension names in correct order
            `unsorted_addresstuple` : list of Strings - ['[dim2].[elem4]','[dim5].[elem1]',...]

        :Returns:
            `tuple` : ('[dim1].[elem2]','[dim2].[elem4]',...)
        '''
        sorted_addresstupple = []
        for dimension in dimension_order:
            address_element = [item for item in unsorted_addresstuple if item.startswith('[' + dimension + '].')]
            sorted_addresstupple.append(address_element[0])
        return tuple(sorted_addresstupple)


    def create_annotation(self, annotation):
        ''' create Annotation
            :Parameters:
                `annotation` : instance of Annotation class

            :Returns:
                `string` : the response
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
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.create_Annotation(annotation)

    def get_annotation(self, id):
        ''' get an annotation from any cube from TM1 Server
            :Parameters:
                `id` : String, the identifier of the annotation to be returned

            :Returns:
                `Annotation` : an instance of the annoation class
        '''
        try:
            request = "/api/v1/Annotations('{}')?$expand=DimensionalContext($select=Name)".format(id)
            annotation_as_json = self._client.GET(request=request)
            return Annotation.from_json(annotation_as_json)
        except(ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_annotation(annotation)


    def update_annotation(self, annotation):
        ''' update Annotation on TM1 Server
            :Parameters:
                `annotation` : instance of Annotation class

            :Notes:
                updateable attributes:
                    commentValue
        '''
        try:
            request = "/api/v1/Annotations('{}')".format(annotation._id)
            return self._client.PATCH(request=request, data=annotation.body)
        except(ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.update_annotation(annotation)

    def delete_annotation(self, id):
        ''' delete Annotation on TM1 Server
            :Parameters:
                `id` : string, the id of Annotation

            :Returns:
                `string` : the response
        '''
        try:
            request = "/api/v1/Annotations('{}')".format(id)
            return self._client.DELETE(request=request)
        except(ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.delete_annotation(id)


    def create_subset(self, subset):
        ''' create the given subset on the TM1 Server
            :Parameters:
                `subset` : Subset
                    the subset to be created

            :Returns:
                `string` : the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + subset._dimension_name +  '\')/Hierarchies(\'' + subset._dimension_name\
                      + '\')/Subsets'
            response = self._client.POST(request, subset.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.create_subset(subset)

    def get_subset(self, name_dimension, name_subset):
        ''' get a subset from the TM1 Server
            :Parameters:
                `name_dimension` : string, name of the dimension
                `name_subset` : string, name of the subset

            :Returns:
                `subset` : instance of the Subset class
        '''
        try:
            request = '/api/v1/Dimensions(\'' + name_dimension +  '\')/Hierarchies(\'' + name_dimension\
                      + '\')/Subsets(\'' + name_subset + '\')?$expand=*'
            response = self._client.GET(request=request)
            return Subset.from_json(response)
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.get_subset(name_dimension, name_subset)

    def update_subset(self, subset):
        ''' update a subset on the TM1 Server
            :Parameters:
                `subset` : Subset
                    the new subset

            :Returns:
                `string` : the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + subset._dimension_name +  '\')/Hierarchies(\'' + subset._dimension_name\
                      + '\')/Subsets(\'' + subset._subset_name + '\')'
            response = self._client.PATCH(request=request, data=subset.body)
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.update_subset(subset)

    def delete_subset(self, name_dimension, name_subset):
        ''' delete a subset on the TM1 Server
            :Parameters:
                `name_dimension` : String, name of the dimension
                `name_subset` : String, name of the subset

            :Returns:
                `string` : the response
        '''
        try:
            request = '/api/v1/Dimensions(\'' + name_dimension +  '\')/Hierarchies(\'' + name_dimension\
                      + '\')/Subsets(\'' + name_subset + '\')'
            response = self._client.DELETE(request=request,data='')
            return response
        except (ConnectionError, ConnectionAbortedError):
            self._client = httpClientTM1(self._ip, self._port, self._user, self._password, self._ssl)
            self.delete_subset(name_dimension, name_subset)


class Server():
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
        self.cliebt_message_port_number = server_as_dict['ClientMessagePortNumber']
        self.http_port_number = server_as_dict['HTTPPortNumber']
        self.using_ssl = server_as_dict['UsingSSL']
        self.accepting_clients = server_as_dict['AcceptingClients']



class Subset():
    ''' Abstraction of the TM1 Subset

        :Notes:
            Done and tested.

            unittests available.

            subset type
                class handles subset type implicitly. According to this logic:
                    self._elements is not [] -> static
                    self._expression is not None -> dyamic
                    self._expression is not None and self._elements is not [] -> dynamic
    '''
    def __init__(self, dimension_name, subset_name, expression = None, elements = []):
        ''' Constructor
            :Parameters:
                `dimension_name` : string
                `subset_name` : string
                `expression` : string
                `elements` : List of element names

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
        return cls(dimension_name = subset_as_dict["UniqueName"][1:subset_as_dict["UniqueName"].find('].[')],
                   subset_name = subset_as_dict['Name'],
                   expression = subset_as_dict['Expression'],
                   elements = [element['Name'] for element in subset_as_dict['Elements']]
                   if not subset_as_dict['Expression'] else [])

    @property
    def body(self):
        ''' same logic here as in TM1 : when subset has expression its dynamic, otherwise static
        '''
        if self._expression:
            return self._construct_body_dynamic()
        else:
            return self._construct_body_static()

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
        self._elements = elements

    def _construct_body_dynamic(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['@odata.type'] = 'ibm.tm1.api.v1.Subset'
        body_as_dict['Name'] = self._subset_name
        body_as_dict['Expression'] = self._expression
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)

    def _construct_body_static(self):
        body_as_dict = collections.OrderedDict()
        body_as_dict['@odata.type'] = 'ibm.tm1.api.v1.Subset'
        body_as_dict['Name'] = self._subset_name

        elements_in_list = []
        for element in self._elements:
            elements_in_list.append('Dimensions(\'' + self._dimension_name + '\')/Hierarchies(\'' +
                                    self._dimension_name + '\')/Elements(\'' + element + '\')')
            body_as_dict['Elements@odata.bind'] = elements_in_list
        return json.dumps(body_as_dict, ensure_ascii=False, sort_keys=False)


class View:
    ''' Abstraction on TM1 View
        serves as a parentclass for MDXView and NativeView

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
            user calls get_view_data_structured from TM1Queries function to retrieve data from View

        :Notes:
            Done and tested.
    '''
    def __init__(self, cube, name, MDX):
        View.__init__(self, cube, name)
        self._MDX = MDX

    @property
    def body(self):
        return self.construct_body()

    def construct_body(self):
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._MDX
        return json.dumps(mdx_view_as_dict, ensure_ascii=False, sort_keys=False)


class NativeView(View):
    ''' Abstraction on TM1 Nativeview

        :usecase:
            user defines view with this class and creates it on TM1 Server.
            user calls get_view_data_structured from TM1Queries function to retrieve data from View

        :Notes:
            Done and tested.
    '''
    def __init__(self, name_cube, name_view, suppress_empty_columns=False, suppress_empty_rows=False,
                 format_string="0.#########\fG|0|", titles = [], columns = [], rows = []):
        View.__init__(self, name_cube, name_view)
        self._suppress_empty_columns = False
        self._suppress_empty_rows = False
        self._format_string = format_string
        self._titles = titles
        self._columns = columns
        self._rows = rows


    @classmethod
    def from_json(cls, view_as_json, titles_as_json, columns_as_json, rows_as_json):
        ''' Alternative constructor
                :Parameters:
                    `view_as_json` : string, JSON
                        response of this request /api/v1/Cubes('x')/Views('y')?$expand=*
                    `titles_as_json` : string, JSON
                        response of this request /api/v1/Cubes('x')/Views('y')/Titles?$expand=*
                    `columns_as_json` : string, JSON
                        response of this request /api/v1/Cubes('x')/Views('y')/Columns?$expand=*
                    `rows_as_json` : string, JSON
                        response of this request /api/v1/Cubes('x')/Views('y')/Rows?$expand=*

                :Returns:
                    `View` : an instance of this class
        '''
        view_as_dict = json.loads(view_as_json)
        titles_as_dict = json.loads(titles_as_json)
        rows_as_dict = json.loads(rows_as_json)
        columns_as_dict = json.loads(columns_as_json)

        titles, columns, rows = [], [], []
        for selection in titles_as_dict['value']:
            subset_as_dict = selection['Subset']
            name_dimension = subset_as_dict['UniqueName'][1:subset_as_dict['UniqueName'].find('].[')]
            name_subset = subset_as_dict['Name']
            selected = selection['Selected']['Name']
            titles.append(ViewTitleSelection(name_dimension, name_subset, selected))

        for i, axe in enumerate([columns_as_dict, rows_as_dict]):
            for selection in axe['value']:
                subset_as_dict = selection['Subset']
                name_dimension = subset_as_dict['UniqueName'][1:subset_as_dict['UniqueName'].find('].[')]
                name_subset = subset_as_dict['Name']
                axis_selection = ViewAxisSelection(name_dimension, name_subset)
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

    def set_suppress_empty_cells(self, value):
        self.set_suppress_empty_columns(value)
        self.set_suppress_empty_rows(value)

    def set_suppress_empty_columns(self, value):
        self._suppress_empty_columns = value

    def set_suppress_empty_rows(self, value):
        self._suppress_empty_rows = value

    def set_format_string(self, new_format):
        self._format_string = new_format

    def add_column(self, dimension, subset):
        view_axis_selection = ViewAxisSelection(dimension, subset)
        self._columns.append(view_axis_selection)

    def remove_column(self, dimension, subset):
        for column in self._columns:
            if column.dimension == dimension and column.subset == subset:
                self._columns.remove(column)

    def add_row(self, dimension, subset):
        view_axis_selection = ViewAxisSelection(dimension, subset)
        self._rows.append(view_axis_selection)

    def remove_row(self, dimension, subset):
        for row in self._rows:
            if row.dimension == dimension and row.subset == subset:
                self._rows.remove(row)

    def add_title(self, dimension, subset, selection):
        view_title_selection = ViewTitleSelection(dimension, subset, selection)
        self._titles.append(view_title_selection)

    def remove_title(self, dimension, subset):
        for title in self._titles:
            if title.dimension == dimension and title.subset == subset:
                self._titles.remove(title)

    def _construct_body(self):
        top_json = "{\"@odata.type\": \"ibm.tm1.api.v1.NativeView\",\"Name\": \"" + self._name +"\","
        columns_json = ','.join([str(column) for column in self._columns])
        rows_json = ','.join([str(row) for row in self._rows])
        titles_json = ','.join([str(title) for title in self._titles])
        bottom_json = "\"SuppressEmptyColumns\": " + str(self._suppress_empty_columns).lower() + \
                      ",\"SuppressEmptyRows\":" + str(self._suppress_empty_rows).lower() + \
                      ",\"FormatString\": \"" + self._format_string + "\"}"
        return top_json + '\"Columns\":[' + columns_json + '],\"Rows\":[' + rows_json + \
                    '],\"Titles\":[' + titles_json + '],' + bottom_json

class ViewAxisSelection:
    def __init__(self, dimension, subset, hierarchies=None):
        self.dimension = dimension
        self.hierarchies = hierarchies
        self.subset = subset

    def __str__(self):
        s = "\"Subset@odata.bind\": \"Dimensions('" + self.dimension + "')/Hierarchies('" \
            + self.dimension + "')/Subsets('" + self.subset + "')\""
        return "{" + s + "}"

class ViewTitleSelection:
    def __init__(self, dimension, subset, selection, hierarchies=None):
        self.dimension = dimension
        self.hierarchies = hierarchies
        self.selection = selection
        self.subset = subset

    def __str__(self):
        s1 = "\"Subset@odata.bind\": \"Dimensions('" + self.dimension + "')/Hierarchies('" \
             + self.dimension + "')/Subsets('" + self.subset + "')\""
        s2 = "\"Selected@odata.bind\": \"Dimensions('" + self.dimension + "')/Hierarchies('" \
             + self.dimension + "')/Elements('" + self.selection + "')\""
        return "{" + s1 + "," + s2 + "}"


class Dimension:
    ''' Abstraction of TM1 Dimension.

        :Notes:
            A Dimension is simply a container for hierarchies.
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

class Hierarchy:
    '''

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
        self._elements.append({'Name': name_element, 'Type': type_element})

    def add_edge(self, name_parent_element, name_component_element):
        self._edges.add({'ParentName': name_parent_element, 'ComponentName': name_component_element})



class Annotation:
    ''' abtraction of TM1 Annotation


        :Notes:
            - Class complete and functional for text annotations !
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
        dimensional_context = [{'Name': element} for element in self._dimensional_context]
        body = {}
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

        'Notes': Class complete and functional !!
    '''

    def __init__(self, name, has_security_access=False, ui_data="CubeAction=1511€DataAction=1503€CubeLogChanges=0€",
                 parameters=[], variables=[], variables_ui_data=[], prolog_procedure='', metadata_procedure='',
                 data_procedure='', epilog_procedure='', datasource_type=None, datasource_ascii_decimal_separator='.',
                 datasource_ascii_delimiter_char=';', datasource_ascii_delimiter_type='Character',
                 datasource_ascii_header_records=1, datasource_ascii_quote_character='', datasource_ascii_thousand_separator=',',
                 datasource_data_source_name_for_client='', datasource_data_source_name_for_server='', datasource_password='',
                 datasource_user_name='', datasource_query='', datasource_uses_unicode=True, datasource_view=''):
        '''default Constructor
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
        self.prolog_procedure = prolog_procedure
        self.metadata_procedure = metadata_procedure
        self.data_procedure = data_procedure
        self.epilog_procedure = epilog_procedure
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
                        a process a as dictionary

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
                   datasource_type=f(process_as_dict['DataSource'],'Type'),
                   datasource_ascii_decimal_separator=f(process_as_dict['DataSource'],'asciiDecimalSeparator'),
                   datasource_ascii_delimiter_char=f(process_as_dict['DataSource'],'asciiDelimiterChar'),
                   datasource_ascii_delimiter_type=f(process_as_dict['DataSource'],'asciiDelimiterType'),
                   datasource_ascii_header_records=f(process_as_dict['DataSource'],'asciiHeaderRecords'),
                   datasource_ascii_quote_character=f(process_as_dict['DataSource'],'asciiQuoteCharacter'),
                   datasource_ascii_thousand_separator=f(process_as_dict['DataSource'],'asciiThousandSeparator'),
                   datasource_data_source_name_for_client=f(process_as_dict['DataSource'],'dataSourceNameForClient'),
                   datasource_data_source_name_for_server=f(process_as_dict['DataSource'],'dataSourceNameForServer'),
                   datasource_password=f(process_as_dict['DataSource'],'password'),
                   datasource_user_name=f(process_as_dict['DataSource'],'userName'),
                   datasource_query=f(process_as_dict['DataSource'],'query'),
                   datasource_uses_unicode=f(process_as_dict['DataSource'],'usesUnicode'),
                   datasource_view=f(process_as_dict['DataSource'],'view'))

    @staticmethod
    def auto_generated_string():
        return "\r\n#****Begin: Generated Statements***\r\n#****End: Generated Statements****\r\n\r\n\r\n"

    @property
    def body(self):
        return self.construct_body()

    def add_variable(self, name_variable, type):
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
        # ' ' is not Space! Character cant be shown by IDE!
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
        self.prolog_procedure = prolog_procedure

    def set_metadata_procedure(self, metadata_procedure):
        self.metadata_procedure = metadata_procedure

    def set_data_procedure(self, data_procedure):
        self.data_procedure =  data_procedure

    def set_epilog_procedure(self, epilog_procedure):
        self.epilog_procedure =  epilog_procedure

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


