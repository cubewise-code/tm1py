# -*- coding: utf-8 -*-

import collections
from typing import List, Tuple, Union

from requests import Response

from TM1py.Exceptions.Exceptions import TM1pyRestException
from TM1py.Objects import View
from TM1py.Objects.MDXView import MDXView
from TM1py.Objects.NativeView import NativeView
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


class ViewService(ObjectService):
    """ Service to handle Object Updates for cube views (NativeViews and MDXViews)
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def create(self, view: Union[MDXView, NativeView], private: bool = False, **kwargs) -> Response:
        """ create a new view on TM1 Server

        :param view: instance of subclass of TM1py.View (TM1py.NativeView or TM1py.MDXView)
        :param private: boolean

        :return: Response
        """
        view_type = "PrivateViews" if private else "Views"
        url = format_url("/api/v1/Cubes('{}')/{}", view.cube, view_type)
        return self._rest.POST(url, view.body, **kwargs)

    def exists(self, cube_name: str, view_name: str, private: bool = None, **kwargs):
        """ Checks if view exists as private, public or both

        :param cube_name:  string, name of the cube
        :param view_name: string, name of the view
        :param private: boolean, if None: check for private and public

        :return boolean tuple
        """
        url_template = "/api/v1/Cubes('{}')/{}('{}')"
        if private is not None:
            url = format_url(url_template, cube_name, "PrivateViews" if private else "Views", view_name)
            return self._exists(url, **kwargs)

        view_types = collections.OrderedDict()
        view_types['PrivateViews'] = False
        view_types['Views'] = False
        for view_type in view_types:
            try:
                url = format_url(url_template, cube_name, view_type, view_name)
                self._rest.GET(url, **kwargs)
                view_types[view_type] = True
            except TM1pyRestException as e:
                if e.status_code != 404:
                    raise e
        return tuple(view_types.values())

    def get(self, cube_name: str, view_name: str, private: bool = False, **kwargs) -> View:
        view_type = "PrivateViews" if private else "Views"
        url = format_url("/api/v1/Cubes('{}')/{}('{}')?$expand=*", cube_name, view_type, view_name)
        response = self._rest.GET(url, **kwargs)
        view_as_dict = response.json()
        if "MDX" in view_as_dict:
            return MDXView(cube_name=cube_name, view_name=view_name, MDX=view_as_dict["MDX"])
        else:
            return self.get_native_view(cube_name=cube_name, view_name=view_name, private=private)

    def get_native_view(self, cube_name: str, view_name: str, private=False, **kwargs) -> NativeView:
        """ Get a NativeView from TM1 Server

        :param cube_name:  string, name of the cube
        :param view_name:  string, name of the native view
        :param private:    boolean

        :return: instance of TM1py.NativeView
        """
        view_type = "PrivateViews" if private else "Views"
        url = format_url(
            "/api/v1/Cubes('{}')/{}('{}')?$expand="
            "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)),Elements($select=Name);"
            "$select=Expression,UniqueName,Name, Alias),  "
            "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)),Elements($select=Name);"
            "$select=Expression,UniqueName,Name,Alias), "
            "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)),Elements($select=Name);"
            "$select=Expression,UniqueName,Name,Alias), "
            "tm1.NativeView/Titles/Selected($select=Name)",
            cube_name, view_type, view_name)
        response = self._rest.GET(url, **kwargs)
        native_view = NativeView.from_json(response.text, cube_name)
        return native_view

    def get_mdx_view(self, cube_name: str, view_name: str, private: bool = False, **kwargs) -> MDXView:
        """ Get an MDXView from TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the MDX view
        :param private: boolean

        :return: instance of TM1py.MDXView
        """
        view_type = 'PrivateViews' if private else 'Views'
        url = format_url("/api/v1/Cubes('{}')/{}('{}')?$expand=*", cube_name, view_type, view_name)
        response = self._rest.GET(url, **kwargs)
        mdx_view = MDXView.from_json(view_as_json=response.text)
        return mdx_view

    def get_all(self, cube_name: str, **kwargs) -> Tuple[List[View], List[View]]:
        """ Get all public and private views from cube.

        :param cube_name: String, name of the cube.
        :return: 2 Lists of TM1py.View instances: private views, public views
        """
        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            url = format_url(
                "/api/v1/Cubes('{}')/{}?$expand="
                "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name);"
                "$select=Expression,UniqueName,Name, Alias),  "
                "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name);"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name);"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Selected($select=Name)",
                cube_name, view_type)
            response = self._rest.GET(url, **kwargs)
            response_as_list = response.json()['value']
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

    def get_all_names(self, cube_name: str, **kwargs) -> Tuple[List[str], List[str]]:
        """
        
        :param cube_name: 
        :return: 
        """
        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            url = format_url("/api/v1/Cubes('{}')/{}?$select=Name", cube_name, view_type)
            response = self._rest.GET(url, **kwargs)
            response_as_list = response.json()['value']

            for view in response_as_list:
                if view_type == "PrivateViews":
                    private_views.append(view['Name'])
                else:
                    public_views.append(view['Name'])

        return private_views, public_views

    def update(self, view: Union[MDXView, NativeView], private: bool = False, **kwargs) -> Response:
        """ Update an existing view

        :param view: instance of TM1py.NativeView or TM1py.MDXView
        :param private: boolean
        :return: response
        """
        view_type = 'PrivateViews' if private else 'Views'
        url = format_url("/api/v1/Cubes('{}')/{}('{}')", view.cube, view_type, view.name)
        response = self._rest.PATCH(url, view.body, **kwargs)
        return response

    def delete(self, cube_name: str, view_name: str, private: bool = False, **kwargs) -> Response:
        """ Delete an existing view (MDXView or NativeView) on the TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: Boolean

        :return: String, the response
        """
        view_type = 'PrivateViews' if private else 'Views'
        url = format_url("/api/v1/Cubes('{}')/{}('{}')", cube_name, view_type, view_name)
        response = self._rest.DELETE(url, **kwargs)
        return response
