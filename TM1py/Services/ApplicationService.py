# -*- coding: utf-8 -*-

from TM1py.Objects import Application
from TM1py.Exceptions import TM1pyException


class ApplicationService:
    """ Service to Read and Write TM1 Applications
    """

    def __init__(self, tm1_rest):
        """

        :param tm1_rest:
        """
        self._rest = tm1_rest

    def get(self, path):
        """ Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        :param path: path through folder structur to application. For instance: "Finance/P&L.xlsx"
        :return: Return application as binary. Can be dumped to file:
            with open("out.xlsx", "wb") as out:
                out.write(content)
        """
        mid = "".join(['/Contents(\'{}\')'.format(element) for element in path.split('/')])
        request = "/api/v1/Contents('Applications')" + mid[:-2] + ".blob')/Document/Content"
        response = self._rest.GET(request)
        content = response.content

        return Application(path, content)

    def delete(self, path, application_type, application_name, access='public'):
        """ Create Planning Analytics application process reference

        Parameters
        ----------
        path : str
            path through folder structur to delete the applications entry. For instance: "Finance/Reports"
        application_type: str
            type of the to be deleted application entry. Can be 'Process', 'Cube', 'View', 'Dimension', 'Subset', 'Chore', 'Extr', 'Blob','Document'
        application_name: str
            name of the to be deleted application entry
        access_type: string, optional
            Access level of the to be deleted object. Default = 'public'. Allowed values: 'private' or 'public'

        Returns
        -------
        response
        """

        # Check if application_type supported
        if application_type.lower() not in ['process', 'cube', 'view', 'dimension', 'subset', 'chore', 'extr', 'blob', 'document', 'folder']:
            raise ValueError("The application type {} doesn't exists in the ApplicationTypeCollection.".format(application_type))

        contents = 'PrivateContents' if access == 'private' else 'Contents'

        if application_type == 'Folder':
            mid = "".join(['/Contents(\'{}\')'.format(element) for element in path.split('/')])
            request = "/api/v1/Contents('Applications')" + mid[:-2] + "')/" + contents + "('" + application_name + "')"
        else:
            mid = "".join(['/Contents(\'{}\')'.format(element) for element in path.split('/')])
            request = "/api/v1/Contents('Applications')" + mid[:-2] + "')/" + contents + "('" + application_name + "." + application_type.lower() + "')"

        response = self._rest.DELETE(request)
        return response   

    def create(self, path, application_type, application_name, object_reference_list='None', access_type='public'):
        """ Create Planning Analytics application process reference

        Parameters
        ----------
        path : str
            path through folder structur to create the applications entry. For instance: "Finance/Reports"
        application_type: str
            type of the created application entry. Can be 'Process', 'Cube', 'View', 'Dimension', 'Subset', 'Chore', 'Link', 'Folder','Document'
        application_name: str
            name of the created application entry
        object_reference_list: list, optional
            Names of the referenced elements in list format. ['Load_actuals'] or ['GL Actuals','My View']
            app type: 'Folder' -> no value required
            app type: 'Process', 'Cube', 'Dimension', 'Chore' -> 1 elem list e.g. ['Process name']
            app type: 'Link' -> 1 elem list e.g. ['http://ibm.com']
            app type: 'Document' -> 1 elem list e.g. ['C:\\MyDocs\\Report.xlsx']
            app type: 'View' -> 2 elem list e.g. ['Cube name','View name']
            app type: 'Subset' -> 3 elem list e.g. ['Dim name','Hier name','Sub name']
        access_type: string, optional
            Access level of created object. Default = 'public'. Allowed values: 'private' or 'public'

        Returns
        -------
        response
        """
        contents = 'PrivateContents' if access_type.lower() == 'private' else 'Contents'
        application_type = application_type.lower().capitalize()

        # Check if application_type supported
        if application_type not in ['Process', 'Cube', 'View', 'Dimension', 'Subset', 'Chore', 'Link', 'Folder', 'Document']:
            raise ValueError("The application type {} doesn't exists in the ApplicationTypeCollection.".format(application_type))

        # Check object_reference_list
        if not object_reference_list and application_type != 'Folder':
            raise ValueError("Object_reference_list cannot be empty if {} application type used.".format(application_type.lower()), 404)

        # Check if object_parent_reference provided
        if (len(object_reference_list) < 2 and application_type == 'View') or (len(object_reference_list) < 3 and application_type == 'Subset'):
            raise ValueError("Object_reference_list required additional values if {} application type used.".format(application_type.lower()))

        object_reference = object_reference_list[0]
        # Create odataType and odataBind
        if application_type in ['Dimension', 'Chore', 'Cube']:
            odataType = '"@odata.type":"tm1.{}Reference"'.format(application_type)
            odataBind = '"{}@odata.bind": "{}s(\'{}\')"'.format(application_type, application_type, object_reference_list[0])
        elif application_type == 'View':
            application_parent_type = 'Cube'
            odataType = '"@odata.type": "tm1.{}Reference"'.format(application_type)
            odataBind = '"{}@odata.bind": "{}s(\'{}\')/{}s(\'{}\')"'.format(application_type, application_parent_type, object_reference_list[0], application_type, object_reference_list[1])
        elif application_type == 'Subset':
            application_parent_type = 'Dimension'
            odataType = '"@odata.type": "tm1.{}Reference"'.format(application_type)
            odataBind = '"{}@odata.bind": "{}s(\'{}\')/Hierarchies(\'{}\')/{}s(\'{}\')"'.format(application_type, application_parent_type, object_reference_list[0], object_reference_list[1], application_type, object_reference_list[2])
        elif application_type == 'Process':
            odataType = '"@odata.type": "tm1.{}Reference"'.format(application_type)
            odataBind = '"{}@odata.bind": "{}es(\'{}\')"'.format(application_type, application_type, object_reference_list[0])
        elif application_type == 'Link':
            odataType = '"@odata.type": "#ibm.tm1.api.v1.Link"'
            odataBind = '"URL": "{}"'.format(object_reference_list[0])
        elif application_type in ['Folder','Document']:
            odataType = '"@odata.type": "#ibm.tm1.api.v1.{}"'.format(application_type)

        mid = "".join(['/Contents(\'{}\')'.format(element) for element in path.split('/')])

        request = "/api/v1/Contents('Applications')" + mid[:-2] + "')/" + contents

        if application_type in ['Document', 'Folder']:
            body = '{ \
            ' + odataType + ', \
            "Name": "' + application_name + '" \
            }'
        else:
            body = '{ \
            ' + odataType + ', \
            "Name":"' + application_name + '", \
            ' + odataBind + ' \
            }'

        response = self._rest.POST(request, body)

        if application_type == 'Document':
            request = "/api/v1/Contents('Applications')" + mid[:-2] + "')\
            /" + contents + "('" + application_name + ".blob')/Document/Content"
            data = open(object_reference_list[0], 'rb').read()
            response = self._rest.PUT(request, data)

        return response


