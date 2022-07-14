# -*- coding: utf-8 -*-
import json
import random
from typing import List, Iterable, Dict

from requests import Response

from TM1py.Objects.Cube import Cube
from TM1py.Services.CellService import CellService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Services.ViewService import ViewService
from TM1py.Utils import format_url, require_version, require_admin, case_and_space_insensitive_equals


class CubeService(ObjectService):
    """ Service to handle Object Updates for TM1 Cubes

    """

    def __init__(self, rest: RestService):
        # to avoid Circular dependency of modules
        from TM1py.Services.AnnotationService import AnnotationService
        super().__init__(rest)
        self.cells = CellService(rest)
        self.views = ViewService(rest)
        self.annotations = AnnotationService(rest)

    def create(self, cube: Cube, **kwargs) -> Response:
        """ create new cube on TM1 Server

        :param cube: instance of TM1py.Cube
        :return: response
        """
        url = "/api/v1/Cubes"
        return self._rest.POST(url=url, data=cube.body, **kwargs)

    def get(self, cube_name: str, **kwargs) -> Cube:
        """ get cube from TM1 Server

        :param cube_name:
        :return: instance of TM1py.Cube
        """
        url = format_url("/api/v1/Cubes('{}')?$expand=Dimensions($select=Name)", cube_name)
        response = self._rest.GET(url=url, **kwargs)
        cube = Cube.from_json(response.text)
        # cater for potential EnableSandboxDimension=T setup
        if case_and_space_insensitive_equals(cube.dimensions[0], "Sandboxes"):
            cube.dimensions = cube.dimensions[1:]
        return cube

    def get_last_data_update(self, cube_name: str, **kwargs) -> str:
        url = format_url("/api/v1/Cubes('{}')/LastDataUpdate/$value", cube_name)
        response = self._rest.GET(url=url, **kwargs)
        return response.text

    def get_all(self, **kwargs) -> List[Cube]:
        """ get all cubes from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        url = "/api/v1/Cubes?$expand=Dimensions($select=Name)"
        response = self._rest.GET(url, **kwargs)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response.json()['value']]
        return cubes

    def get_model_cubes(self, **kwargs) -> List[Cube]:
        """ Get all Cubes without } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        url = "/api/v1/ModelCubes()?$expand=Dimensions($select=Name)"
        response = self._rest.GET(url, **kwargs)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response.json()['value']]
        return cubes

    def get_control_cubes(self, **kwargs) -> List[Cube]:
        """ Get all Cubes with } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        url = "/api/v1/ControlCubes()?$expand=Dimensions($select=Name)"
        response = self._rest.GET(url, **kwargs)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response.json()['value']]
        return cubes

    def get_number_of_cubes(self, skip_control_cubes: bool = False, **kwargs) -> int:
        """ Ask TM1 Server for count of cubes

        :skip_control_cubes: bool, True will exclude control cubes from count
        :return: int, count
        """ 
        if skip_control_cubes:
            response = self._rest.GET(url=format_url("/api/v1/ModelCubes()?$select=Name&$top=0&$count"), **kwargs)
            return int(response.json()['@odata.count'])

        return int(self._rest.GET(url=format_url("/api/v1/Cubes/$count"), **kwargs).text)

    def get_measure_dimension(self, cube_name: str, **kwargs) -> str:
        url = format_url(
            "/api/v1/Cubes('{}')/Dimensions?$select=Name",
            cube_name)
        response = self._rest.GET(url, **kwargs)
        return response.json()['value'][-1]['Name']

    def update(self, cube: Cube, **kwargs) -> Response:
        """ Update existing cube on TM1 Server

        :param cube: instance of TM1py.Cube
        :return: response
        """
        url = format_url("/api/v1/Cubes('{}')", cube.name)
        return self._rest.PATCH(url, cube.body, **kwargs)

    def update_or_create(self, cube: Cube, **kwargs) -> Response:
        """ update if exists else create

        :param cube:
        :return:
        """
        if self.exists(cube_name=cube.name, **kwargs):
            return self.update(cube=cube, **kwargs)

        return self.create(cube=cube, **kwargs)

    def check_rules(self, cube_name: str, **kwargs) -> Response:
        """ Check rules syntax for existing cube on TM1 Server

        :param cube_name: name of a cube
        :return: response
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.CheckRules", cube_name)

        response = self._rest.POST(url, **kwargs)
        errors = response.json()["value"]
        return errors

    @require_admin
    def delete(self, cube_name: str, **kwargs) -> Response:
        """ Delete a cube in TM1

        :param cube_name:
        :return: response
        """
        url = format_url("/api/v1/Cubes('{}')", cube_name)
        return self._rest.DELETE(url, **kwargs)

    def exists(self, cube_name: str, **kwargs) -> bool:
        """ Check if a cube exists. Return boolean.

        :param cube_name: 
        :return: Boolean 
        """
        url = format_url("/api/v1/Cubes('{}')", cube_name)
        return self._exists(url, **kwargs)

    def get_all_names(self, skip_control_cubes: bool = False, **kwargs) -> List[str]:
        """ Ask TM1 Server for list of all cube names
        
        :skip_control_cubes: bool, True will exclude control cubes from list
        :return: List of Strings
        """
        url = format_url(
                "/api/v1/{}?$select=Name",
                'ModelCubes()' if skip_control_cubes else 'Cubes'
        )

        response = self._rest.GET(url, **kwargs)
        cubes = list(entry['Name'] for entry in response.json()['value'])
        return cubes

    def get_all_names_with_rules(self, skip_control_cubes: bool = False, **kwargs) -> List[str]:
        """ Ask TM1 Server for list of all cube names that have rules
        
        :skip_control_cubes: bool, True will exclude control cubes from list
        :return: List of Strings
        """
        url = format_url(
                "/api/v1/{}?$select=Name,Rules&$filter=Rules ne null",
                'ModelCubes()' if skip_control_cubes else 'Cubes'
        )

        response = self._rest.GET(url, **kwargs)
        cubes = list(cube['Name'] for cube in response.json()['value'])
        return cubes

    def get_all_names_without_rules(self, skip_control_cubes: bool = False, **kwargs) -> List[str]:
        """ Ask TM1 Server for list of all cube names that do not have rules
        :skip_control_cubes: bool, True will exclude control cubes from list
        :return: List of Strings
        """

        url = format_url(
                "/api/v1/{}?$select=Name,Rules&$filter=Rules eq null",
                'ModelCubes()' if skip_control_cubes else 'Cubes'
        )

        response = self._rest.GET(url, **kwargs)
        cubes = list(cube['Name'] for cube in response.json()['value'])
        return cubes

    def get_dimension_names(self, cube_name: str, skip_sandbox_dimension: bool = True, **kwargs) -> List[str]:
        """ get name of the dimensions of a cube in their correct order

        :param cube_name:
        :param skip_sandbox_dimension:
        :return:  List : [dim1, dim2, dim3, etc.]
        """
        url = format_url("/api/v1/Cubes('{}')/Dimensions?$select=Name", cube_name)
        response = self._rest.GET(url, **kwargs)
        dimension_names = [element['Name'] for element in response.json()['value']]
        if skip_sandbox_dimension and dimension_names[0] == CellService.SANDBOX_DIMENSION:
            return dimension_names[1:]
        return dimension_names

    def search_for_dimension(self, dimension_name: str, skip_control_cubes: bool = False,
                             **kwargs) -> List[str]:
        """ Ask TM1 Server for list of cube names that contain specific dimension

        :param dimension_name: string, valid dimension name (case insensitive)
        :param skip_control_cubes: bool, True will exclude control cubes from result
        """
        url = format_url(
            "/api/v1/{}?$select=Name&$filter=Dimensions/any(d: replace(tolower(d/Name), ' ', '') eq '{}')",
            'ModelCubes()' if skip_control_cubes else 'Cubes',
            dimension_name.lower().replace(' ', '')
        )
        response = self._rest.GET(url, **kwargs)
        cubes = list(entry['Name'] for entry in response.json()['value'])
        return cubes

    def search_for_dimension_substring(self, substring: str, skip_control_cubes: bool = False,
                                       **kwargs) -> Dict[str, List[str]]:
        """ Ask TM1 Server for a dictinary of cube names with the dimension whose name contains the substring

        :param substring: string to search for in dim name
        :param skip_control_cubes: bool, True will exclude control cubes from result
        """
        substring = substring.lower().replace(' ', '')

        url = format_url(
            "/api/v1/{}?$select=Name&$filter=Dimensions/any(d: contains(replace(tolower(d/Name), ' ', ''),'{}'))" +
            "&$expand=Dimensions($select=Name;$filter=contains(replace(tolower(Name), ' ', ''), '{}'))",
            'ModelCubes()' if skip_control_cubes else 'Cubes',
            substring,
            substring)

        response = self._rest.GET(url, **kwargs)
        cube_dict = {entry['Name']: [dim['Name'] for dim in entry['Dimensions']] for entry in response.json()['value']}
        return cube_dict
    
    def search_for_rule_substring(self, substring: str, skip_control_cubes: bool = False, case_insensitive=True,
                                  space_insensitive=True, **kwargs) -> List[Cube]:
        """ get all cubes from TM1 Server as TM1py.Cube instances where rules for given cube contain specified substring

        :param substring: string to search for in rules
        :param skip_control_cubes: bool, True will exclude control cubes from result
        :param case_insensitive: case agnostic search
        :param space_insensitive: space agnostic search
        :return: List of TM1py.Cube instances
        """
        substring = substring.lower().replace(' ', '')

        url_filter = "Rules ne null and contains("
        if case_insensitive and space_insensitive:
            url_filter += format_url("tolower(replace(Rules, ' ', '')),'{}')", substring)
        elif case_insensitive:
            url_filter += format_url("tolower(Rules),'{}')", substring)
        elif space_insensitive:
            url_filter += format_url("replace(Rules, ' ', ''),'{}')", substring)
        else:
            url_filter += format_url("Rules,'{}')", substring)

        url = f"/api/v1/{'ModelCubes()' if skip_control_cubes else 'Cubes'}?$filter={url_filter}" \
              f"&$expand=Dimensions($select=Name)"

        response = self._rest.GET(url, **kwargs)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response.json()['value']]
        return cubes   

    @require_version(version="11.4")
    def get_storage_dimension_order(self, cube_name: str, **kwargs) -> List[str]:
        """ Get the storage dimension order of a cube

        :param cube_name:
        :return: List of dimension names
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.DimensionsStorageOrder()?$select=Name", cube_name)
        response = self._rest.GET(url, **kwargs)
        return [dimension["Name"] for dimension in response.json()["value"]]

    @require_admin
    @require_version(version="11.4")
    def update_storage_dimension_order(self, cube_name: str, dimension_names: Iterable[str]) -> float:
        """ Update the storage dimension order of a cube

        :param cube_name:
        :param dimension_names:
        :return:  Float: -23.076489699337078 (percent change in memory usage)
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.ReorderDimensions", cube_name)
        payload = dict()
        payload['Dimensions@odata.bind'] = [format_url("Dimensions('{}')", dimension)
                                            for dimension
                                            in dimension_names]
        response = self._rest.POST(url=url, data=json.dumps(payload))
        return response.json()["value"]

    @require_admin
    @require_version(version="11.6")
    def load(self, cube_name: str, **kwargs) -> Response:
        """ Load the cube into memory on the server

        :param cube_name:
        :return:
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.Load", cube_name)
        return self._rest.POST(url=url, **kwargs)

    @require_admin
    @require_version(version="11.6")
    def unload(self, cube_name: str, **kwargs) -> Response:
        """ Unload the cube from memory

        :param cube_name:
        :return:
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.Unload", cube_name)
        return self._rest.POST(url=url, **kwargs)

    def lock(self, cube_name: str, **kwargs) -> Response:
        """ Locks the cube to prevent any users from modifying it

        :param cube_name:
        :return:
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.Lock", cube_name)
        return self._rest.POST(url=url, **kwargs)

    def unlock(self, cube_name: str, **kwargs) -> Response:
        """ Unlocks the cube to allow modifications

        :param cube_name:
        :return:
        """
        url = format_url("/api/v1/Cubes('{}')/tm1.Unlock", cube_name)
        return self._rest.POST(url=url, **kwargs)

    def get_random_intersection(self, cube_name: str, unique_names: bool = False) -> List[str]:
        """ Get a random Intersection in a cube
        used mostly for regression testing.
        Not optimized, in terms of performance. Function Loads ALL elements for EACH dim...

        :param cube_name: 
        :param unique_names: unique names instead of plain element names 
        :return: List of elements
        """
        from TM1py.Services import DimensionService
        dimension_service = DimensionService(self._rest)
        dimensions = self.get_dimension_names(cube_name)
        elements = []
        for dimension in dimensions:
            hierarchy = dimension_service.get(dimension).default_hierarchy
            element = random.choice(list((hierarchy.elements.keys())))
            if unique_names:
                element = '[{}].[{}]'.format(dimension, element)
            elements.append(element)
        return elements
