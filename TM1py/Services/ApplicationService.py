# -*- coding: utf-8 -*-
from TM1py.Objects.Application import DocumentApplication, ApplicationTypes, CubeApplication, ChoreApplication, \
    FolderApplication, LinkApplication, ProcessApplication, DimensionApplication, SubsetApplication, ViewApplication

from TM1py.Services.ObjectService import ObjectService


class ApplicationService(ObjectService):
    """ Service to Read and Write TM1 Applications
    """

    def __init__(self, tm1_rest):
        """

        :param tm1_rest:
        """
        super().__init__(tm1_rest)
        self._rest = tm1_rest

    def get(self, path, application_type, name, private=False):
        """ Retrieve Planning Analytics Application

        :param path:
        :param application_type:
        :param name:
        :param private:
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        # documents require special treatment
        if application_type == ApplicationTypes.DOCUMENT:
            return self.get_document(path=path, name=name)

        if not application_type == ApplicationTypes.FOLDER:
            name += application_type.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if path.strip() != '':
            mid = "".join(["/Contents('{}')".format(element) for element in path.split('/')])
        base_url = "/api/v1/Contents('Applications'){dynamic_mid}/{contents}('{application_name}')".format(
            dynamic_mid=mid,
            contents=contents,
            application_name=name)

        if application_type == ApplicationTypes.CUBE:
            response = self._rest.GET(base_url + "?$expand=Cube($select=Name)")
            return CubeApplication(path=path, name=name, cube_name=response.json()["Cube"]["Name"])

        elif application_type == ApplicationTypes.CHORE:
            response = self._rest.GET(base_url + "?$expand=Chore($select=Name)")
            return ChoreApplication(path=path, name=name, chore_name=response.json()["Chore"]["Name"])

        elif application_type == ApplicationTypes.DIMENSION:
            response = self._rest.GET(base_url + "?$expand=Dimension($select=Name)")
            return DimensionApplication(path=path, name=name, dimension_name=response.json()["Dimension"]["Name"])

        elif application_type == ApplicationTypes.FOLDER:
            # implicit TM1pyException if doesn't exist
            self._rest.GET(base_url)
            return FolderApplication(path=path, name=name)

        elif application_type == ApplicationTypes.LINK:
            # implicit TM1pyException if doesn't exist
            self._rest.GET(base_url)
            response = self._rest.GET(base_url + "?$expand=*")
            return LinkApplication(path=path, name=name, url=response.json()["URL"])

        elif application_type == ApplicationTypes.PROCESS:
            response = self._rest.GET(base_url + "?$expand=Process($select=Name)")
            return ProcessApplication(path=path, name=name, process_name=response.json()["Process"]["Name"])

        elif application_type == ApplicationTypes.SUBSET:
            response = self._rest.GET(
                base_url +
                "?$expand=Subset($select=Name;$expand=Hierarchy($select=Name;$expand=Dimension($select=Name)))")
            return SubsetApplication(
                path=path,
                name=name,
                dimension_name=response.json()["Subset"]["Hierarchy"]["Dimension"]["Name"],
                hierarchy_name=response.json()["Subset"]["Hierarchy"]["Name"],
                subset_name=response.json()["Subset"]["Name"])

        elif application_type == ApplicationTypes.VIEW:
            response = self._rest.GET(base_url + "?$expand=View($select=Name;$expand=Cube($select=Name))")
            return ViewApplication(
                path=path,
                name=name,
                cube_name=response.json()["View"]["Cube"]["Name"],
                view_name=response.json()["View"]["Name"])

    def get_document(self, path, name, private=False):
        """ Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        :param path: path through folder structure to application. For instance: "Finance/P&L.xlsx"
        :param name: name of the application
        :param private: boolean
        :return: Return DocumentApplication
        """
        if not name.endswith(ApplicationTypes.DOCUMENT.suffix):
            name += ApplicationTypes.DOCUMENT.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = "".join(["/Contents('{}')".format(element) for element in path.split('/')])
        request = "/api/v1/Contents('Applications'){dynamic_mid}/{contents}('{name}')/Document/Content".format(
            dynamic_mid=mid,
            contents=contents,
            name=name)
        response = self._rest.GET(request)
        return DocumentApplication(path, name, response.content)

    def delete(self, path, application_type, application_name, private=False):
        """ Create Planning Analytics application process reference

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
            mid = "".join(["/Contents('{}')".format(element) for element in path.split('/')])
        request = "/api/v1/Contents('Applications'){dynamic_mid}/{contents}('{application_name}')".format(
            dynamic_mid=mid,
            contents=contents,
            application_name=application_name)

        return self._rest.DELETE(request)

    def create(self, application, private=False):
        """ Create Planning Analytics application

        :param application: instance of Application
        :param private: boolean
        :return:
        """

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if application.path.strip() != '':
            mid = "".join(["/Contents('{}')".format(element) for element in application.path.split('/')])
        request = "/api/v1/Contents('Applications')" + mid + "/" + contents
        response = self._rest.POST(request, application.body)

        if application.application_type == ApplicationTypes.DOCUMENT:
            request = "/api/v1/Contents('Applications'){dynamic_mid}/{contents}('{application_name}.blob')/Document/" \
                      "Content".format(dynamic_mid=mid, contents=contents, application_name=application.name)
            response = self._rest.PUT(request, application.content, self.BINARY_HTTP_HEADER)

        return response

    def exists(self, path, application_type, name, private=False):
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER:
            name += application_type.suffix

        contents = 'PrivateContents' if private else 'Contents'
        mid = ""
        if path.strip() != '':
            mid = "".join(["/Contents('{}')".format(element) for element in path.split('/')])
        base_url = "/api/v1/Contents('Applications'){dynamic_mid}/{contents}('{application_name}')".format(
            dynamic_mid=mid,
            contents=contents,
            application_name=name)
        return self._exists(base_url)

    def create_document_from_file(self, path_to_file, path, name, private=False):
        with open(path_to_file, 'rb') as file:
            app = DocumentApplication(path=path, name=name, content=file.read())
            return self.create(application=app, private=private)
