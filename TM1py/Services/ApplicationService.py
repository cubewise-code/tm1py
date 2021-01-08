# -*- coding: utf-8 -*-
from typing import Union

from requests import Response

from TM1py.Objects.Application import DocumentApplication, ApplicationTypes, CubeApplication, ChoreApplication, \
    FolderApplication, LinkApplication, ProcessApplication, DimensionApplication, SubsetApplication, ViewApplication, \
    Application
from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url


class ApplicationService(ObjectService):
    """ Service to Read and Write TM1 Applications
    """

    def __init__(self, tm1_rest: RestService):
        """

        :param tm1_rest:
        """
        super().__init__(tm1_rest)
        self._rest = tm1_rest

    def get(self, path: str, application_type: Union[str, ApplicationTypes], name: str, private: bool = False,
            **kwargs) -> Application:
        """ Retrieve Planning Analytics Application

        :param path: path with forward slashes
        :param application_type: str or ApplicationType from Enum
        :param name:
        :param private:
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        # documents require special treatment
        if application_type == ApplicationTypes.DOCUMENT:
            return self.get_document(path=path, name=name, private=private, **kwargs)

        if not application_type == ApplicationTypes.FOLDER:
            name += application_type.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if path.strip() != '':
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split('/')])

        base_url = format_url(
            "/api/v1/Contents('Applications')" + mid + "/" + contents + "('{application_name}')",
            application_name=name)

        if application_type == ApplicationTypes.CUBE:
            response = self._rest.GET(url=base_url + "?$expand=Cube($select=Name)", **kwargs)
            return CubeApplication(path=path, name=name, cube_name=response.json()["Cube"]["Name"])

        elif application_type == ApplicationTypes.CHORE:
            response = self._rest.GET(url=base_url + "?$expand=Chore($select=Name)", **kwargs)
            return ChoreApplication(path=path, name=name, chore_name=response.json()["Chore"]["Name"])

        elif application_type == ApplicationTypes.DIMENSION:
            response = self._rest.GET(url=base_url + "?$expand=Dimension($select=Name)", **kwargs)
            return DimensionApplication(path=path, name=name, dimension_name=response.json()["Dimension"]["Name"])

        elif application_type == ApplicationTypes.FOLDER:
            # implicit TM1pyException if application doesn't exist
            self._rest.GET(url=base_url, **kwargs)
            return FolderApplication(path=path, name=name)

        elif application_type == ApplicationTypes.LINK:
            # implicit TM1pyException if application doesn't exist
            self._rest.GET(url=base_url, **kwargs)
            response = self._rest.GET(base_url + "?$expand=*", **kwargs)
            return LinkApplication(path=path, name=name, url=response.json()["URL"])

        elif application_type == ApplicationTypes.PROCESS:
            response = self._rest.GET(url=base_url + "?$expand=Process($select=Name)", **kwargs)
            return ProcessApplication(path=path, name=name, process_name=response.json()["Process"]["Name"])

        elif application_type == ApplicationTypes.SUBSET:
            url = "".join([
                base_url,
                "?$expand=Subset($select=Name;$expand=Hierarchy($select=Name;$expand=Dimension($select=Name)))"])
            response = self._rest.GET(
                url=url,
                **kwargs)
            return SubsetApplication(
                path=path,
                name=name,
                dimension_name=response.json()["Subset"]["Hierarchy"]["Dimension"]["Name"],
                hierarchy_name=response.json()["Subset"]["Hierarchy"]["Name"],
                subset_name=response.json()["Subset"]["Name"])

        elif application_type == ApplicationTypes.VIEW:
            response = self._rest.GET(
                url=base_url + "?$expand=View($select=Name;$expand=Cube($select=Name))",
                **kwargs)
            return ViewApplication(
                path=path,
                name=name,
                cube_name=response.json()["View"]["Cube"]["Name"],
                view_name=response.json()["View"]["Name"])

    def get_document(self, path: str, name: str, private: bool = False, **kwargs) -> DocumentApplication:
        """ Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        :param path: path through folder structure to application. For instance: "Finance/P&L.xlsx"
        :param name: name of the application
        :param private: boolean
        :return: Return DocumentApplication
        """
        if not name.endswith(ApplicationTypes.DOCUMENT.suffix):
            name += ApplicationTypes.DOCUMENT.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = "".join([format_url("/Contents('{}')", element) for element in path.split('/')])
        url = format_url(
            "/api/v1/Contents('Applications')" + mid + "/" + contents + "('{name}')/Document/Content",
            name=name)

        response = self._rest.GET(url, **kwargs)
        return DocumentApplication(path, name, response.content)

    def delete(self, path: str, application_type: Union[str, ApplicationTypes], application_name: str,
               private: bool = False, **kwargs) -> Response:
        """ Delete Planning Analytics application reference

        :param path: path through folder structure to delete the applications entry. For instance: "Finance/Reports"
        :param application_type: type of the to be deleted application entry
        :param application_name: name of the to be deleted application entry
        :param private: Access level of the to be deleted object
        :return:
        """

        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER:
            application_name += application_type.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if path.strip() != '':
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split('/')])

        url = format_url(
            "/api/v1/Contents('Applications')" + mid + "/" + contents + "('{application_name}')",
            application_name=application_name)
        return self._rest.DELETE(url, **kwargs)

    def create(self, application: Union[Application, DocumentApplication], private: bool = False, **kwargs) -> Response:
        """ Create Planning Analytics application

        :param application: instance of Application
        :param private: boolean
        :return:
        """

        contents = 'PrivateContents' if private else 'Contents'

        mid = ""
        if application.path.strip() != '':
            mid = "".join([format_url("/Contents('{}')", element) for element in application.path.split('/')])
        url = "/api/v1/Contents('Applications')" + mid + "/" + contents
        response = self._rest.POST(url, application.body, **kwargs)

        if application.application_type == ApplicationTypes.DOCUMENT:
            url = format_url(
                "/api/v1/Contents('Applications')" + mid + "/" + contents + "('{name}.blob')/Document/Content",
                name=application.name)
            response = self._rest.PUT(url, application.content, headers=self.BINARY_HTTP_HEADER, **kwargs)

        return response

    def exists(self, path: str, application_type: Union[str, ApplicationTypes], name: str,
               private: bool = False, **kwargs) -> bool:
        """ Check if application exists

        :param path:
        :param application_type:
        :param name:
        :param private:
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER:
            name += application_type.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if path.strip() != '':
            mid = "".join(["/Contents('{}')".format(element) for element in path.split('/')])

        url = format_url(
            "/api/v1/Contents('Applications')" + mid + "/" + contents + "('{application_name}')",
            application_name=name)
        return self._exists(url, **kwargs)

    def create_document_from_file(self, path_to_file: str, application_path: str, application_name: str,
                                  private: bool = False, **kwargs) -> Response:
        """ Create DocumentApplication in TM1 from local file

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :return:
        """
        with open(path_to_file, 'rb') as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.create(application=application, private=private, **kwargs)
