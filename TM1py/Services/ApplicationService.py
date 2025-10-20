# -*- coding: utf-8 -*-
import json
from typing import Union

from requests import Response

from TM1py.Objects.Application import (
    Application,
    ApplicationTypes,
    ChoreApplication,
    CubeApplication,
    DimensionApplication,
    DocumentApplication,
    FolderApplication,
    LinkApplication,
    ProcessApplication,
    SubsetApplication,
    ViewApplication,
)
from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url, verify_version


class ApplicationService(ObjectService):
    """Service to Read and Write TM1 Applications"""

    def __init__(self, tm1_rest: RestService):
        """

        :param tm1_rest:
        """
        super().__init__(tm1_rest)
        self._rest = tm1_rest

    def get_all_public_root_names(self, **kwargs):
        """
        Retrieve all public root application names.

        :param kwargs: Additional arguments for the REST request.
        :return: List of public root application names.
        """
        url = "/Contents('Applications')/Contents"
        response = self._rest.GET(url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])
        return applications

    def get_all_private_root_names(self, **kwargs):

        url = "/Contents('Applications')/PrivateContents"
        response = self._rest.GET(url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])
        return applications

    def get_names(self, path: str, private: bool = False, **kwargs):
        """Retrieve Planning Analytics Application names in given path

        :param path: path with forward slashes
        :param private: boolean
        :return: list of application names
        """
        contents = "PrivateContents" if private else "Contents"
        mid = ""
        if path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split("/")])
        base_url = "/api/v1/Contents('Applications')" + mid + "/" + contents

        response = self._rest.GET(url=base_url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])

        return applications

    def get(
        self, path: str, application_type: Union[str, ApplicationTypes], name: str, private: bool = False, **kwargs
    ) -> Application:
        """Retrieve Planning Analytics Application

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

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        mid = ""
        if path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split("/")])

        base_url = format_url(
            "/Contents('Applications')" + mid + "/" + contents + "('{application_name}')", application_name=name
        )

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
            url = "".join(
                [
                    base_url,
                    "?$expand=Subset($select=Name;$expand=Hierarchy($select=Name;$expand=Dimension($select=Name)))",
                ]
            )
            response = self._rest.GET(url=url, **kwargs)
            return SubsetApplication(
                path=path,
                name=name,
                dimension_name=response.json()["Subset"]["Hierarchy"]["Dimension"]["Name"],
                hierarchy_name=response.json()["Subset"]["Hierarchy"]["Name"],
                subset_name=response.json()["Subset"]["Name"],
            )

        elif application_type == ApplicationTypes.VIEW:
            response = self._rest.GET(url=base_url + "?$expand=View($select=Name;$expand=Cube($select=Name))", **kwargs)
            return ViewApplication(
                path=path,
                name=name,
                cube_name=response.json()["View"]["Cube"]["Name"],
                view_name=response.json()["View"]["Name"],
            )

    def get_document(self, path: str, name: str, private: bool = False, **kwargs) -> DocumentApplication:
        """Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        :param path: path through folder structure to application. For instance: "Finance/P&L.xlsx"
        :param name: name of the application
        :param private: boolean
        :return: Return DocumentApplication
        """
        if not name.endswith(ApplicationTypes.DOCUMENT.suffix) and not verify_version(
            required_version="12", version=self.version
        ):
            name += ApplicationTypes.DOCUMENT.suffix

        contents = "PrivateContents" if private else "Contents"
        mid = "".join([format_url("/Contents('{}')", element) for element in path.split("/")])
        url = format_url("/Contents('Applications')" + mid + "/" + contents + "('{name}')/Document/Content", name=name)

        content = self._rest.GET(url, **kwargs).content

        url = format_url("/Contents('Applications')" + mid + "/" + contents + "('{name}')/Document", name=name)
        document_fields = self._rest.GET(url, **kwargs).json()

        return DocumentApplication(
            path=path,
            name=name,
            content=content,
            file_id=document_fields.get("ID"),
            file_name=document_fields.get("Name"),
            last_updated=document_fields.get("LastUpdated"),
        )

    def delete(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        application_name: str,
        private: bool = False,
        **kwargs,
    ) -> Response:
        """Delete Planning Analytics application reference

        :param path: path through folder structure to delete the applications entry. For instance: "Finance/Reports"
        :param application_type: type of the to be deleted application entry
        :param application_name: name of the to be deleted application entry
        :param private: Access level of the to be deleted object
        :return:
        """

        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        mid = ""
        if path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split("/")])

        url = format_url(
            "/Contents('Applications')" + mid + "/" + contents + "('{application_name}')",
            application_name=application_name,
        )
        return self._rest.DELETE(url, **kwargs)

    def rename(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        application_name: str,
        new_application_name: str,
        private: bool = False,
        **kwargs,
    ):
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        mid = ""
        if path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in path.split("/")])

        url = format_url(
            "/Contents('Applications')" + mid + "/" + contents + "('{application_name}')/tm1.Move",
            application_name=application_name,
        )
        data = {"Name": new_application_name}

        return self._rest.POST(url, data=json.dumps(data), **kwargs)

    def create(self, application: Union[Application, DocumentApplication], private: bool = False, **kwargs) -> Response:
        """Create Planning Analytics application

        :param application: instance of Application
        :param private: boolean
        :return:
        """

        contents = "PrivateContents" if private else "Contents"

        mid = ""
        if application.path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in application.path.split("/")])
        url = "/Contents('Applications')" + mid + "/" + contents
        response = self._rest.POST(url, application.body, **kwargs)

        if application.application_type == ApplicationTypes.DOCUMENT:
            url = format_url(
                "/Contents('Applications')" + mid + "/" + contents + "('{name}{suffix}')/Document/Content",
                name=application.name,
                suffix=".blob" if not verify_version(required_version="12", version=self.version) else "",
            )
            response = self._rest.PUT(url, application.content, headers=self.binary_http_header, **kwargs)

        return response

    def update(self, application: Union[Application, DocumentApplication], private: bool = False, **kwargs) -> Response:
        """Update Planning Analytics application

        :param application: instance of Application
        :param private: boolean
        :return:
        """

        contents = "PrivateContents" if private else "Contents"

        mid = ""
        if application.path.strip() != "":
            mid = "".join([format_url("/Contents('{}')", element) for element in application.path.split("/")])

        if application.application_type == ApplicationTypes.DOCUMENT:
            url = format_url(
                "/Contents('Applications')" + mid + "/" + contents + "('{name}{extension}')/Document/Content",
                name=application.name,
                extension="" if verify_version("12", self.version) else ".blob"
            )
            response = self._rest.PATCH(url=url, data=application.content, headers=self.binary_http_header, **kwargs)
        else:
            url = "/Contents('Applications')" + mid + "/" + contents
            response = self._rest.POST(url, application.body, **kwargs)

        return response

    def update_or_create(
        self, application: Union[Application, DocumentApplication], private: bool = False, **kwargs
    ) -> Response:
        """Update or create Planning Analytics application

        :param application: instance of Application
        :param private: boolean
        :return: Response
        """
        if self.exists(
            path=application.path,
            application_type=application.application_type,
            name=application.name,
            private=private,
            **kwargs,
        ):
            response = self.update(application=application, private=private, **kwargs)
        else:
            response = self.create(application=application, private=private, **kwargs)
        return response

    def update_or_create_document_from_file(
        self, path: str, name: str, path_to_file: str, private: bool = False, **kwargs
    ) -> Response:
        """Update or create application from file

        :param path: application path on server, i.e. 'Finance/Reports'
        :param name: name of the application on server, i.e. 'Flash.xlsx'
        :param path_to_file: full local file path of file, i.e. 'C:\\Users\\User\\Flash.xslx'
        :param private: access level of the object
        :return: Response
        """

        if self.exists(path=path, application_type=ApplicationTypes.DOCUMENT, name=name, private=private):
            response = self.update_document_from_file(
                path_to_file=path_to_file, application_path=path, application_name=name, private=private
            )
        else:
            response = self.create_document_from_file(
                path_to_file=path_to_file, application_path=path, application_name=name, private=private
            )

        return response

    def exists(
        self, path: str, application_type: Union[str, ApplicationTypes], name: str, private: bool = False, **kwargs
    ) -> bool:
        """Check if application exists

        :param path:
        :param application_type:
        :param name:
        :param private:
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        mid = ""
        if path.strip() != "":
            mid = "".join(["/Contents('{}')".format(element) for element in path.split("/")])

        url = format_url(
            "/Contents('Applications')" + mid + "/" + contents + "('{application_name}')", application_name=name
        )
        return self._exists(url, **kwargs)

    def create_document_from_file(
        self, path_to_file: str, application_path: str, application_name: str, private: bool = False, **kwargs
    ) -> Response:
        """Create DocumentApplication in TM1 from local file

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.create(application=application, private=private, **kwargs)

    def update_document_from_file(
        self, path_to_file: str, application_path: str, application_name: str, private: bool = False, **kwargs
    ) -> Response:
        """Update DocumentApplication in TM1 from local file

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.update(application=application, private=private, **kwargs)
