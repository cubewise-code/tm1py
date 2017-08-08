import json

from TM1py.Objects.Cube import Cube
from TM1py.Services.ObjectService import ObjectService


class CubeService(ObjectService):
    def __init__(self, rest):
        super().__init__(rest)

    def create(self, cube):
        """ create new cube on TM1 Server

        :param cube:
        :return: response
        """
        request = "/api/v1/Cubes"
        return self._rest.POST(request, cube.body)

    def get(self, cube_name):
        """ get cube from TM1 Server

        :param cube_name:
        :return: instance of TM1py.Cube
        """
        request = "/api/v1/Cubes('{}')?$expand=Dimensions($select=Name)".format(cube_name)
        response = self._rest.GET(request)
        cube = Cube.from_json(response)
        return cube

    def get_all(self):
        """ get all cubes from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = "/api/v1/Cubes?$expand=Dimensions($select=Name)"
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def get_model_cubes(self):
        """ Get all Cubes without } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = "/api/v1/ModelCubes()?$expand=Dimensions($select=Name)"
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def get_control_cubes(self):
        """ Get all Cubes with } prefix from TM1 Server as TM1py.Cube instances

        :return: List of TM1py.Cube instances
        """
        request = "/api/v1/ControlCubes()?$expand=Dimensions($select=Name)"
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)
        cubes = [Cube.from_dict(cube_as_dict=cube) for cube in response_as_dict['value']]
        return cubes

    def update(self, cube):
        """ Update existing cube on TM1 Server

        :param cube: instance of TM1py.Cube
        :return: response
        """
        request = "/api/v1/Cubes('{}')".format(cube.name)
        return self._rest.PATCH(request, cube.body)

    def delete(self, cube_name):
        """ Delete a cube in TM1

        :param cube_name:
        :return: response
        """
        request = "/api/v1/Cubes('{}')".format(cube_name)
        return self._rest.DELETE(request)

    def exists(self, cube_name):
        """ Check if a cube exists. Return boolean.
        Assumption: Connection is established and functional.

        :param cube_name: 
        :return: Boolean 
        """
        request = "/api/v1/Cubes('{}')".format(cube_name)
        return super(CubeService, self).exists(request)

    def get_all_names(self):
        """ Ask TM1 Server for list with all cube names

        :return: List of Strings
        """
        response = self._rest.GET('/api/v1/Cubes?$select=Name', '')
        cubes = json.loads(response)['value']
        list_cubes = list(entry['Name'] for entry in cubes)
        return list_cubes

    def get_dimension_names(self, cube_name):
        """ get name of the dimensions of a cube in their correct order

        :param cube_name: String
        :return:  List : [dim1, dim2, dim3, etc.]
        """
        request = "/api/v1/Cubes('{}')/Dimensions?$select=Name".format(cube_name)
        response = self._rest.GET(request, '')
        response_as_dict = json.loads(response)['value']
        dimension_names = [element['Name'] for element in response_as_dict]
        return dimension_names
