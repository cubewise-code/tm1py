# -*- coding: utf-8 -*-

import collections
from typing import List, Tuple, Union, Iterable, Optional

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
        url = format_url("/Cubes('{}')/{}", view.cube, view_type)
        return self._rest.POST(url, view.body, **kwargs)

    def exists(self, cube_name: str, view_name: str, private: bool = None, **kwargs):
        """ Checks if view exists as private, public or both

        :param cube_name:  string, name of the cube
        :param view_name: string, name of the view
        :param private: boolean, if None: check for private and public

        :return boolean tuple
        """
        url_template = "/Cubes('{}')/{}('{}')"
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

    def get(self, cube_name: str, view_name: str, private: bool = False, element_properties: Optional[Iterable[str]] = ('Name',), **kwargs) -> View:
        view_type = "PrivateViews" if private else "Views"
        url = format_url("/Cubes('{}')/{}('{}')?$expand=*", cube_name, view_type, view_name)
        response = self._rest.GET(url, **kwargs)
        view_as_dict = response.json()
        if "MDX" in view_as_dict:
            return MDXView(cube_name=cube_name, view_name=view_name, MDX=view_as_dict["MDX"])
        else:
            return self.get_native_view(cube_name=cube_name, view_name=view_name, element_properties=element_properties, private=private)

    def get_native_view(self, cube_name: str, view_name: str, private=False, element_properties: Optional[Iterable[str]] = ('Name',), **kwargs) -> NativeView:
        """ Get a NativeView from TM1 Server

        :param cube_name:  string, name of the cube
        :param view_name:  string, name of the native view
        :param private:    boolean

        :return: instance of TM1py.NativeView
        """
        view_type = "PrivateViews" if private else "Views"

        if element_properties:
            element_properties = ",".join(element_properties)
            element_properties = f',Elements($select={element_properties})'
        else:
            element_properties = ''

        url = format_url(
            "/Cubes('{}')/{}('{}')?$expand="
            "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)){};"
            "$select=Expression,UniqueName,Name, Alias),  "
            "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)){};"
            "$select=Expression,UniqueName,Name,Alias), "
            "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;"
            "$expand=Dimension($select=Name)){};"
            "$select=Expression,UniqueName,Name,Alias), "
            "tm1.NativeView/Titles/Selected($select=Name)",
            cube_name, view_type, view_name, element_properties, element_properties, element_properties)
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
        url = format_url("/Cubes('{}')/{}('{}')?$expand=*", cube_name, view_type, view_name)
        response = self._rest.GET(url, **kwargs)
        mdx_view = MDXView.from_json(view_as_json=response.text)
        return mdx_view

    def get_all(self, cube_name: str, include_elements: bool = True, **kwargs) -> Tuple[List[View], List[View]]:
        """ Get all public and private views from cube.
        :param cube_name: String, name of the cube.
        :param include_elements: false to return view details without elements, faster
        :return: 2 Lists of TM1py.View instances: private views, public views
        """

        element_filter = ";$top=0" if not include_elements else ""

        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            url = format_url(
                "/Cubes('{}')/{}?$expand="
                "tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name, Alias),  "
                "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Selected($select=Name)",
                cube_name, view_type, element_filter, element_filter, element_filter)
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
            url = format_url("/Cubes('{}')/{}?$select=Name", cube_name, view_type)
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
        url = format_url("/Cubes('{}')/{}('{}')", view.cube, view_type, view.name)
        response = self._rest.PATCH(url, view.body, **kwargs)
        return response

    def update_or_create(self, view: Union[MDXView, NativeView], private: bool = False, **kwargs) -> Response:
        """ update if exists, else create

        :param view:
        :param private:
        :param kwargs:
        :return:
        """
        if self.exists(view.cube, view.name, private=private, **kwargs):
            return self.update(view, private=private, **kwargs)

        return self.create(view, private=private, **kwargs)

    def delete(self, cube_name: str, view_name: str, private: bool = False, **kwargs) -> Response:
        """ Delete an existing view (MDXView or NativeView) on the TM1 Server

        :param cube_name: String, name of the cube
        :param view_name: String, name of the view
        :param private: Boolean

        :return: String, the response
        """
        view_type = 'PrivateViews' if private else 'Views'
        url = format_url("/Cubes('{}')/{}('{}')", cube_name, view_type, view_name)
        response = self._rest.DELETE(url, **kwargs)
        return response

    def search_subset_in_native_views(self, dimension_name: str = None, subset_name: str = None, cube_name: str = None,
                                      include_elements: bool = False, **kwargs) -> Tuple[List[View], List[View]]:
        """ Get all public and private native views that utilize specified dimension subset

        :param dimension_name: string, valid dimension name with subset to query
        :param subset_name: string, valid subset name to search for in views
        :param cube_name: str, optionally specify cube to search, otherwise will search all cubes
        :param include_elements: false to return view details without elements, faster
        :return: 2 Lists of TM1py.View instances: private views, public views
        """

        dimension_name = dimension_name.lower().replace(' ', '')
        subset_name = subset_name.lower().replace(' ', '')

        element_filter = ";$top=0" if not include_elements else ""
        if cube_name:
            base_url = format_url(
                "/Cubes?$select=Name&$filter=replace(tolower(Name),' ', '') eq '{}'",
                cube_name.lower().replace(' ', ''))
        else:
            base_url = "/Cubes?$select=Name"

        private_views, public_views = [], []
        for view_type in ('PrivateViews', 'Views'):
            url = base_url + format_url(
                "&$expand={}($filter=isof(tm1.NativeView) and"
                "("
                "(tm1.NativeView/Rows/any (r: replace(tolower(r/Subset/Name), ' ', '') eq '{}' "
                "and replace(tolower(r/Subset/Hierarchy/Dimension/Name), ' ', '') eq '{}'))"
                "or"
                "(tm1.NativeView/Columns/any (c: replace(tolower(c/Subset/Name), ' ', '') eq '{}' "
                "and replace(tolower(c/Subset/Hierarchy/Dimension/Name), ' ', '') eq '{}')) "
                "or"
                "(tm1.NativeView/Titles/any (t: replace(tolower(t/Subset/Name), ' ', '') eq '{}' "
                "and replace(tolower(t/Subset/Hierarchy/Dimension/Name), ' ', '') eq '{}'))"
                ");"
                "$expand=tm1.NativeView/Rows/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name, Alias),  "
                "tm1.NativeView/Columns/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Subset($expand=Hierarchy($select=Name;"
                "$expand=Dimension($select=Name)),Elements($select=Name{});"
                "$select=Expression,UniqueName,Name,Alias), "
                "tm1.NativeView/Titles/Selected($select=Name))",
                view_type, subset_name, dimension_name, subset_name, dimension_name,
                subset_name, dimension_name, element_filter, element_filter, element_filter
            )

            response = self._rest.GET(url, **kwargs)
            response_as_list = response.json()['value']
            for cube in response_as_list:
                for view_as_dict in cube[view_type]:
                    view = NativeView.from_dict(view_as_dict, cube['Name'])
                    if view_type == "PrivateViews":
                        private_views.append(view)
                    else:
                        public_views.append(view)

        return private_views, public_views

    def is_mdx_view(self, cube_name: str, view_name: str, private=False, **kwargs):
        url_template = "/Cubes('{}')/{}('{}')?select=Name"
        if private is not None:
            url = format_url(url_template, cube_name, "PrivateViews" if private else "Views", view_name)

        response = self._rest.GET(url, **kwargs)
        # e.g.: "ibm.tm1.api.v1.NativeView"
        odata_type = response.json()["@odata.type"]
        if odata_type.split('.')[-1] == "NativeView":
            return False
        return True

    def is_native_view(self, cube_name: str, view_name: str, private=False):
        return not self.is_mdx_view(cube_name, view_name, private)
