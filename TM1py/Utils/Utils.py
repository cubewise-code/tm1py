import collections
import json
import sys

from TM1py.Objects.Server import Server
from TM1py.Objects.Process import Process

if sys.version[0] == '2':
    import httplib as http_client
else:
    import http.client as http_client


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


def sort_addresstuple(cube_dimensions, unsorted_addresstuple):
    """ Sort the given mixed up addresstuple

    :param cube_dimensions: list of dimension names in correct order
    :param unsorted_addresstuple: list of Strings - ['[dim2].[elem4]','[dim1].[elem2]',...]

    :return:
        Tuple: ('[dim1].[elem2]','[dim2].[elem4]',...)
    """
    sorted_addresstupple = []
    for dimension in cube_dimensions:
        # could be more than one hierarchy!
        address_elements = [item for item in unsorted_addresstuple if item.startswith('[' + dimension + '].')]
        # address_elements could be ( [dim1].[hier1].[elem1], [dim1].[hier2].[elem3] )
        for address_element in address_elements:
            sorted_addresstupple.append(address_element)
    return tuple(sorted_addresstupple)


def build_content_from_cellset(raw_cellset_as_dict, cell_properties, top=None):
    """ transform raw cellset data into concise dictionary

    :param raw_cellset_as_dict:
    :param cell_properties:
    :param top: Maximum Number of cells
    :return:
    """
    content_as_dict = CaseAndSpaceInsensitiveTuplesDict()

    cube_dimensions = [dim['Name'] for dim in raw_cellset_as_dict['Cube']['Dimensions']]

    axe0_as_dict = raw_cellset_as_dict['Axes'][0]
    axe1_as_dict = raw_cellset_as_dict['Axes'][1]

    ordinal_cells = 0

    ordinal_axe2 = 0
    # get coordinates on axe 2: Title
    # if there are no elements on axe 2 assign empty list to elements_on_axe2
    if len(raw_cellset_as_dict['Axes']) > 2:
        axe2_as_dict = raw_cellset_as_dict['Axes'][2]
        tuples_as_dict = axe2_as_dict['Tuples'][ordinal_axe2]['Members']
        elements_on_axe2 = [member['Element']['UniqueName'] for member in tuples_as_dict]
    else:
        elements_on_axe2 = []

    ordinal_axe1 = 0
    for i in range(axe1_as_dict['Cardinality']):
        # get coordinates on axe 1: Rows
        tuples_as_dict = axe1_as_dict['Tuples'][ordinal_axe1]['Members']
        elements_on_axe1 = [member['Element']['UniqueName'] for member in tuples_as_dict]
        ordinal_axe0 = 0
        for j in range(axe0_as_dict['Cardinality']):
            # get coordinates on axe 0: Columns
            tuples_as_dict = axe0_as_dict['Tuples'][ordinal_axe0]['Members']
            elements_on_axe0 = [member['Element']['UniqueName'] for member in tuples_as_dict]
            coordinates = elements_on_axe0 + elements_on_axe2 + elements_on_axe1
            coordinates_sorted = sort_addresstuple(cube_dimensions, coordinates)
            # get cell properties
            content_as_dict[coordinates_sorted] = {}
            for cell_property in cell_properties:
                value = raw_cellset_as_dict['Cells'][ordinal_cells][cell_property]
                content_as_dict[coordinates_sorted][cell_property] = value
            ordinal_axe0 += 1
            ordinal_cells += 1
            if top is not None and ordinal_cells >= top:
                break
        if top is not None and ordinal_cells >= top:
            break
        ordinal_axe1 += 1
    return content_as_dict


def element_names_from_element_unqiue_names(element_unique_names):
    """ Get tuple of simple element names from the full element unique names
    
    :param element_unique_names: tuple of element unique names ([dim1].[hier1].[elem1], ... )
    :return: tuple of element names: (elem1, elem2, ... )
    """
    return tuple([unique_name[unique_name.rfind('].[') + 3:-1]
                  for unique_name
                  in element_unique_names])


def build_pandas_dataframe_from_cellset(cellset, multiindex=True, sort_index=True):
    """
    
    :param cellset: 
    :param multiindex: True or False
    :param sort_index: Boolean to control sorting in result DataFrame
    :return: 
    """
    import pandas as pd

    cellset_clean = {}
    for coordinates, cell in cellset.items():
        element_names = element_names_from_element_unqiue_names(coordinates)
        cellset_clean[element_names] = cell['Value']

    dimension_names = tuple([unique_name[1:unique_name.find('].[')] for unique_name in coordinates])

    # create index
    keylist = list(cellset_clean.keys())
    index = pd.MultiIndex.from_tuples(keylist, names=dimension_names)

    # create DataFrame
    values = list(cellset_clean.values())
    df = pd.DataFrame(values, index=index, columns=["Values"])

    if not multiindex:
        df.reset_index(inplace=True)
    if sort_index:
        df.sort_index(inplace=True)
    return df


def load_bedrock_from_github(bedrock_process_name):
    """ Load bedrock from GitHub as TM1py.Process instance
    
    :param name_bedrock_process: 
    :return: 
    """
    import requests
    url = 'https://raw.githubusercontent.com/MariusWirtz/bedrock/master/json/{}.json'.format(bedrock_process_name)
    process_as_json = requests.get(url).text
    return Process.from_json(process_as_json)


def load_all_bedrocks_from_github():
    """ Load all Bedrocks from GitHub as TM1py.Process instances
    
    :return: 
    """
    import requests
    # Connect to Bedrock github repo and load the names of all Bedrocks
    url = "https://api.github.com/repos/MariusWirtz/bedrock/contents/json?ref=master"
    raw_github_data = requests.get(url).json()
    all_bedrocks = [entry['name'] for entry in raw_github_data]
    # instantiate TM1py.Process instances from github-json content
    url_to_bedrock = 'https://raw.githubusercontent.com/MariusWirtz/bedrock/master/json/{}'
    return [Process.from_json(requests.get(url_to_bedrock.format(bedrock)).text) for bedrock in all_bedrocks]


class CaseAndSpaceInsensitiveDict(collections.MutableMapping):
    """A case-and-space-insensitive dict-like object with String keys.

    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``adjusted_items``, ``adjusted_keys``.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. 

    However, querying and contains testing is case insensitive:
        elements = TM1pyElementsDictionary()
        elements['Travel Expesnses'] = 100
        elements['travelexpenses'] == 100 # True

    Entries are ordered
    """

    def __init__(self, data=None, **kwargs):
        self._store = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the adjusted cased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower().replace(' ', '')] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower().replace(' ', '')][1]

    def __delitem__(self, key):
        del self._store[key.lower().replace(' ', '')]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def adjusted_items(self):
        """Like iteritems(), but with all adjusted keys."""
        return (
            (adjusted_key, key_value[1])
            for (adjusted_key, key_value)
            in self._store.items()
        )

    def adjusted_keys(self):
        """Like keys(), but with all adjusted keys."""
        return (
            adjusted_key
            for (adjusted_key, key_value)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections.Mapping):
            other = CaseAndSpaceInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.adjusted_items()) == dict(other.adjusted_items())

    # Copy is required
    def copy(self):
        return CaseAndSpaceInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))


class CaseAndSpaceInsensitiveTuplesDict(collections.MutableMapping):
    """A case-and-space-insensitive dict-like object with String-Tuples Keys.

    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``adjusted_items``, ``adjusted_keys``.

    All keys are expected to be tuples of strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. 

    However, querying and contains testing is case insensitive:
        data = CaseAndSpaceInsensitiveTuplesDict()
        data[('[Business Unit].[UK]', '[Scenario].[Worst Case]')] = 1000
        data[('[BusinessUnit].[UK]', '[Scenario].[worstcase]')] == 1000 # True
        data[('[Business Unit].[UK]', '[Scenario].[Worst Case]')] == 1000 # True

    Entries are ordered
    """

    def __init__(self, data=None, **kwargs):
        self._store = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the adjusted cased key for lookups, but store the actual
        # key alongside the value.
        self._store[tuple([item.lower().replace(' ', '') for item in key])] = (key, value)

    def __getitem__(self, key):
        return self._store[tuple([item.lower().replace(' ', '') for item in key])][1]

    def __delitem__(self, key):
        del self._store[tuple([item.lower().replace(' ', '') for item in key])]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def adjusted_items(self):
        """Like iteritems(), but with all adjusted keys."""
        return (
            (adjusted_key, key_value[1])
            for (adjusted_key, key_value)
            in self._store.items()
        )

    def adjusted_keys(self):
        """Like keys(), but with all adjusted keys."""
        return (
            adjusted_key
            for (adjusted_key, key_value)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections.Mapping):
            other = CaseAndSpaceInsensitiveTuplesDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.adjusted_items()) == dict(other.adjusted_items())

    # Copy is required
    def copy(self):
        return CaseAndSpaceInsensitiveTuplesDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))