# -*- coding: utf-8 -*-
import json
from collections import namedtuple, OrderedDict
from enum import Enum
from typing import Union, Dict

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url

ApplicationType = namedtuple('ApplicationType', ['value', 'suffix', 'odata_type'])


class ApplicationTypes(Enum):
    CHORE = ApplicationType(1, ".chore", "tm1.ChoreReference")
    CUBE = ApplicationType(2, ".cube", "tm1.CubeReference")
    DIMENSION = ApplicationType(3, ".dimension", "tm1.DimensionReference")
    DOCUMENT = ApplicationType(4, ".blob", "#ibm.tm1.api.v1.Document")
    FOLDER = ApplicationType(5, "", "#ibm.tm1.api.v1.Folder")
    LINK = ApplicationType(6, ".extr", "#ibm.tm1.api.v1.Link")
    PROCESS = ApplicationType(7, ".process", "tm1.ProcessReference")
    SUBSET = ApplicationType(8, ".subset", "tm1.SubsetReference")
    VIEW = ApplicationType(9, ".view", "tm1.ViewReference")

    @classmethod
    def _missing_(cls, value: str) -> ApplicationType:
        for member in cls:
            if member.name.lower() == value.lower():
                return member

    @property
    def suffix(self) -> str:
        return self.value.suffix

    @property
    def odata_type(self) -> str:
        return self.value.odata_type


class Application(TM1Object):

    def __init__(self, path: str, name: str, application_type: Union[ApplicationTypes, str]):
        self.path = path
        # remove suffix from name
        if application_type.suffix and name.endswith(application_type.suffix):
            self.name = name[: - len(application_type.suffix)]
        else:
            self.name = name
        # raise ValueError if not a valid type
        self.application_type = ApplicationTypes(application_type)

    @property
    def application_id(self) -> str:
        return self.path + self.name + self.application_type.suffix

    @property
    def body_as_dict(self) -> Dict:
        body_as_dict = OrderedDict()
        body_as_dict["@odata.type"] = self.application_type.odata_type
        body_as_dict["Name"] = self.name
        return body_as_dict

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        return json.dumps(body_as_dict, ensure_ascii=False)


class ChoreApplication(Application):
    def __init__(self, path: str, name: str, chore_name: str):
        super().__init__(path, name, ApplicationTypes.CHORE)
        self.chore_name = chore_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["Chore@odata.bind"] = format_url("Chores('{}')", self.chore_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class CubeApplication(Application):
    def __init__(self, path: str, name: str, cube_name: str):
        super().__init__(path, name, ApplicationTypes.CUBE)
        self.cube_name = cube_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["Cube@odata.bind"] = format_url("Cubes('{}')", self.cube_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class DimensionApplication(Application):
    def __init__(self, path: str, name: str, dimension_name: str):
        super().__init__(path, name, ApplicationTypes.DIMENSION)
        self.dimension_name = dimension_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["Dimension@odata.bind"] = format_url("Dimensions('{}')", self.dimension_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class DocumentApplication(Application):
    def __init__(self, path: str, name: str, content: bytes):
        super().__init__(path, name, ApplicationTypes.DOCUMENT)
        self.content = content

    def to_xlsx(self, path_to_file: str):
        with open(path_to_file, "wb") as file:
            file.write(self.content)


class FolderApplication(Application):
    def __init__(self, path: str, name: str):
        super().__init__(path, name, ApplicationTypes.FOLDER)


class LinkApplication(Application):
    def __init__(self, path: str, name: str, url: str):
        super().__init__(path, name, ApplicationTypes.LINK)
        self.url = url

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["URL"] = self.url
        return json.dumps(body_as_dict, ensure_ascii=False)


class ProcessApplication(Application):
    def __init__(self, path: str, name: str, process_name: str):
        super().__init__(path, name, ApplicationTypes.PROCESS)
        self.process_name = process_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["Process@odata.bind"] = format_url("Processes('{}')", self.process_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class SubsetApplication(Application):
    def __init__(self, path: str, name: str, dimension_name: str, hierarchy_name: str, subset_name: str):
        super().__init__(path, name, ApplicationTypes.SUBSET)
        self.dimension_name = dimension_name
        self.hierarchy_name = hierarchy_name
        self.subset_name = subset_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["Subset@odata.bind"] = format_url(
            "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')",
            self.dimension_name, self.hierarchy_name, self.subset_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class ViewApplication(Application):
    def __init__(self, path: str, name: str, cube_name: str, view_name: str):
        super().__init__(path, name, ApplicationTypes.VIEW)
        self.cube_name = cube_name
        self.view_name = view_name

    @property
    def body(self) -> str:
        body_as_dict = self.body_as_dict
        body_as_dict["View@odata.bind"] = format_url("Cubes('{}')/Views('{}')", self.cube_name, self.view_name)
        return json.dumps(body_as_dict, ensure_ascii=False)
