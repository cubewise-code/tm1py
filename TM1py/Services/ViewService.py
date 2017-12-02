# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Exceptions.Exceptions import TM1pyException

from TM1py.Objects.NativeView import NativeView
from TM1py.Objects.MDXView import MDXView

from TM1py.Services.ObjectService import ObjectService


class ViewService(ObjectService):
    """ Service to handle Object Updates for cube views (NativeViews and MDXViews)
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def create(self, view, private=True):
        """ create a new view on TM1 Server

        :param view: instance of subclass of TM1py.View (TM1py.NativeView or TM1py.MDXView)
        :param private: boolean

        :return: Response
        """
        view_type = "PrivateViews" if private else "Views"
        request = "/api/v1/Cubes('{}')/{}".format(view.cube, view_type)
        return self._rest.POST(request, view.body)

    def exists(self, cube_name, view_name):
        """ Checks if view exists

        :param cube_name:  string, name of the cube
        :param view_name: string, name of the view

        :return boolean tuple
        """
        view_types = collections.OrderedDict()
        view_types['PrivateViews'] = False
        view_types['Views'] = False

        for view_type in view_types:
            try:
                self._rest.GET("/api/v1/Cubes('{}')/{}('{}')".format(cube_name, view_type, view_name))
                view_types[view_type] = True
            except TM1pyException as e:
                if e._status_code != 404:
                    raise e
        return tuple(view_types.values())

    def get_native_view(self, cube_name, view_name, private=True):
        """ Get a NativeView from TM1 Server

        :param cube_name:  string, name of the cube
        :param view_name:  string, name of the native view
        :param private:    boolean

        :return: instance of TM1py.NativeView
        """
        view_type = "PrivateViews" if private else "Views"
        request = "/api/v1/Cubes('{}')/{}('{}')?$expand=" \
                  "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name, Alias),  " \
                  "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name,Alias), " \
                  "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;" \
                  "$expand=Dimension($select=Name)),Elements($select=Name);" \
                  "$select=Expression,UniqueName,Name,Alias), " \
                  "tm1.NativeView/Titles/Selected($select=Name)".format(cube_name, view_type, view_name)
        view_as_json = self._rest.GET(request)
        native_view = NativeView.from_json(view_as_json, cube_name)
        return native_view

    def get_mdx_view(self, cube_name, view_name, private=True):
        """ Get an MDXView from TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the MDX view
        :param private: boolean

        :return: instance of TM1py.MDXView
        """
        view_type = 'PrivateViews' if private else 'Views'
        request = "/api/v1/Cubes('{}')/{}('{}')?$expand=*".format(cube_name, view_type, view_name)
        view_as_json = self._rest.GET(request)
        mdx_view = MDXView.from_json(view_as_json=view_as_json)
        return mdx_view

    def get_all(self, cube_name):
        """ Get all public and private views from cube.

        :param cube_name: String, name of the cube.
        :return: 2 Lists of TM1py.View instances: private views, public views
        """
        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            request = "/api/v1/Cubes('{}')/{}?$expand=" \
                      "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name, Alias),  " \
                      "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name,Alias), " \
                      "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;" \
                      "$expand=Dimension($select=Name)),Elements($select=Name);" \
                      "$select=Expression,UniqueName,Name,Alias), " \
                      "tm1.NativeView/Titles/Selected($select=Name)".format(cube_name, view_type)
            response = self._rest.GET(request)
            response_as_list = json.loads(response)['value']
            for view_as_dict in response_as_list:
                if view_as_dict['@odata.type'] == '#ibm.tm1.api.v1.MDXView':
                    view = MDXView.from_dict(view_as_dict, cube_name)
                else:
                    view = NativeView.from_dict(view_as_dict, cube_name)
                if view_type == "PrivateViews":
                    private_views.append(view)
                else:
                    public_views.append(view)
        return private_views, public_views

    def get_all_names(self, cube_name):
        """
        
        :param cube_name: 
        :return: 
        """
        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            request = "/api/v1/Cubes('{}')/{}?$select=Name".format(cube_name, view_type)
            response = self._rest.GET(request)
            response_as_list = json.loads(response)['value']
            for view in response_as_list:
                if view_type == "PrivateViews":
                    private_views.append(view['Name'])
                else:
                    public_views.append(view['Name'])
        return private_views, public_views

    def update(self, view, private=True):
        """ Update an existing view

        :param view: instance of TM1py.NativeView or TM1py.MDXView
        :param private: boolean
        :return: response
        """
        view_type = 'PrivateViews' if private else 'Views'
        request = "/api/v1/Cubes('{}')/{}('{}')".format(view.cube, view_type, view.name)
        response = self._rest.PATCH(request, view.body)
        return response

    def delete(self, cube_name, view_name, private=True):
        """ Delete an existing view (MDXView or NativeView) on the TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: Boolean

        :return: String, the response
        """
        view_type = 'PrivateViews' if private else 'Views'
        request = "/api/v1/Cubes('{}')/{}('{}')".format(cube_name, view_type, view_name)
        response = self._rest.DELETE(request)
        return response


