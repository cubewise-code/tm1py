# -*- coding: utf-8 -*-
import json
from collections import namedtuple, OrderedDict
from enum import Enum

from TM1py.Objects.TM1Object import TM1Object


class Application(TM1Object):

    def __init__(self, path, name, application_type):
        self.path = path
        # remove suffix from name
        if application_type.suffix and name.endswith(application_type.suffix):
            self.name = name[: - len(application_type.suffix)]
        else:
            self.name = name
        # raise ValueError if not a valid type
        self.application_type = ApplicationTypes(application_type)

    @property
    def application_id(self):
        return self.path + self.name + self.application_type.suffix

    @property
    def body_as_dict(self):
        body_as_dict = OrderedDict()
        body_as_dict["@odata.type"] = self.application_type.odata_type
        body_as_dict["Name"] = self.name
        return body_as_dict

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        return json.dumps(body_as_dict, ensure_ascii=False)


class ChoreApplication(Application):
    def __init__(self, path, name, chore_name):
        super().__init__(path, name, ApplicationTypes.CHORE)
        self.chore_name = chore_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["Chore@odata.bind"] = "Chores('{}')".format(self.chore_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class CubeApplication(Application):
    def __init__(self, path, name, cube_name):
        super().__init__(path, name, ApplicationTypes.CUBE)
        self.cube_name = cube_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["Cube@odata.bind"] = "Cubes('{}')".format(self.cube_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class DimensionApplication(Application):
    def __init__(self, path, name, dimension_name):
        super().__init__(path, name, ApplicationTypes.DIMENSION)
        self.dimension_name = dimension_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["Dimension@odata.bind"] = "Dimensions('{}')".format(self.dimension_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class DocumentApplication(Application):
    def __init__(self, path, name, content):
        super().__init__(path, name, ApplicationTypes.DOCUMENT)
        self.content = content

    def to_xlsx(self, path_to_file):
        with open(path_to_file, "wb") as file:
            file.write(self.content)


class FolderApplication(Application):
    def __init__(self, path, name):
        super().__init__(path, name, ApplicationTypes.FOLDER)


class LinkApplication(Application):
    def __init__(self, path, name, url):
        super().__init__(path, name, ApplicationTypes.LINK)
        self.url = url

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["URL"] = self.url
        return json.dumps(body_as_dict, ensure_ascii=False)


class ProcessApplication(Application):
    def __init__(self, path, name, process_name):
        super().__init__(path, name, ApplicationTypes.PROCESS)
        self.process_name = process_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["Process@odata.bind"] = "Processes('{}')".format(self.process_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class SubsetApplication(Application):
    def __init__(self, path, name, dimension_name, hierarchy_name, subset_name):
        super().__init__(path, name, ApplicationTypes.SUBSET)
        self.dimension_name = dimension_name
        self.hierarchy_name = hierarchy_name
        self.subset_name = subset_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["Subset@odata.bind"] = "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')".format(
            self.dimension_name, self.hierarchy_name, self.subset_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


class ViewApplication(Application):
    def __init__(self, path, name, cube_name, view_name):
        super().__init__(path, name, ApplicationTypes.VIEW)
        self.cube_name = cube_name
        self.view_name = view_name

    @property
    def body(self):
        body_as_dict = self.body_as_dict
        body_as_dict["View@odata.bind"] = "Cubes('{}')/Views('{}')".format(self.cube_name, self.view_name)
        return json.dumps(body_as_dict, ensure_ascii=False)


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
    def _missing_(cls, value):
        for member in cls:
            if member.name.lower() == value.lower():
                return member

    @property
    def suffix(self):
        return self.value.suffix

    @property
    def odata_type(self):
        return self.value.odata_type
