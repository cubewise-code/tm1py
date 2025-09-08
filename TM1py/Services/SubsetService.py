# -*- coding: utf-8 -*-
import json
from typing import List, Union, Iterable, Optional

from requests import Response

from TM1py.Objects import Subset, Element
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url


class SubsetService(ObjectService):
    """ Service to handle Object Updates for TM1 Subsets (dynamic and static)
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)
        self._process_service = ProcessService(rest)

    def create(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ create subset on the TM1 Server

            :param subset: TM1py.Subset, the subset that shall be created
            :param private: boolean

            :return:
                string: the response
        """
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}",
            subset.dimension_name,
            subset.hierarchy_name,
            subsets)
        response = self._rest.POST(url, subset.body, **kwargs)
        return response

    def get(self, subset_name: str, dimension_name: str, hierarchy_name: str = None, private: bool = False,
            **kwargs) -> Subset:
        """ get a subset from the TM1 Server

            :param subset_name: string, name of the subset
            :param dimension_name: string, name of the dimension
            :param hierarchy_name: string, name of the hierarchy
            :param private: Boolean

            :return: instance of TM1py.Subset
        """
        if not hierarchy_name:
            hierarchy_name = dimension_name
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}('{}')?$expand=Hierarchy($select=Dimension,Name),"
            "Elements($select=Name)&$select=*,Alias", dimension_name, hierarchy_name, subsets, subset_name)
        response = self._rest.GET(url=url, **kwargs)
        return Subset.from_dict(response.json())

    def get_all_names(self, dimension_name: str, hierarchy_name: str = None, private: bool = False,
                      **kwargs) -> List[str]:
        """ get names of all private or public subsets in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param private: Boolean
        :return: List of Strings
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name

        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}?$select=Name",
            dimension_name, hierarchy_name, subsets)
        response = self._rest.GET(url=url, **kwargs)
        subsets = response.json()['value']
        return [subset['Name'] for subset in subsets]

    def update(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ update a subset on the TM1 Server

        :param subset: instance of TM1py.Subset.
        :param private: Boolean
        :return: response
        """
        if subset.is_static:
            return self.update_static_elements(subset=subset, elements=subset.elements, private=private, **kwargs)
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            subset.dimension_name, subset.hierarchy_name, subsets, subset.name)
        return self._rest.PATCH(url=url, data=subset.body, **kwargs)

    def make_static(self, subset_name: str, dimension_name: str, hierarchy_name: str = None,
                    private: bool = False) -> Response:
        """ convert a dynamic subset into static subset on the TM1 Server
        :param subset_name: String, name of the subset
        :param dimension_name: String, name of the dimension
        :param hierarchy_name: String, name of the hierarchy
        :param private: Boolean
        :return: response
        """
        import json
        from collections import OrderedDict
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        payload = OrderedDict()
        payload['Name'] = subset_name
        payload['MakePrivate'] = True if private else False
        payload['MakeStatic'] = True
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url("/Dimensions('{}')/Hierarchies('{}')/{}('{}')/tm1.SaveAs", dimension_name,
                         hierarchy_name, subsets, subset_name)
        return self._rest.POST(url=url, data=json.dumps(payload))

    def update_or_create(self, subset: Subset, private: bool = False, **kwargs) -> Response:
        """ update if exists else create

        :param subset:
        :param private:
        :return:
        """
        if self.exists(
                subset_name=subset.name,
                dimension_name=subset.dimension_name,
                hierarchy_name=subset.hierarchy_name,
                private=private,
                **kwargs):
            return self.update(subset=subset, private=private, **kwargs)

        return self.create(subset=subset, private=private, **kwargs)

    def delete(self, subset_name: str, dimension_name: str, hierarchy_name: str = None,
               private: bool = False, **kwargs) -> Response:
        """ Delete an existing subset on the TM1 Server

        :param subset_name: String, name of the subset
        :param dimension_name: String, name of the dimension
        :param hierarchy_name: String, name of the hierarchy
        :param private: Boolean
        :return:
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            dimension_name, hierarchy_name, subsets, subset_name)
        response = self._rest.DELETE(url=url, **kwargs)
        return response

    def exists(self, subset_name: str, dimension_name: str, hierarchy_name: str = None, private: bool = False,
               **kwargs) -> bool:
        """checks if private or public subset exists

        :param subset_name: 
        :param dimension_name: 
        :param hierarchy_name:
        :param private:
        :return: boolean
        """
        hierarchy_name = hierarchy_name if hierarchy_name else dimension_name
        subset_type = 'PrivateSubsets' if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}('{}')",
            dimension_name, hierarchy_name, subset_type, subset_name)
        return self._exists(url, **kwargs)

    def delete_elements_from_static_subset(self, dimension_name: str, hierarchy_name: str, subset_name: str,
                                           private: bool, **kwargs) -> Response:
        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url(
            "/Dimensions('{}')/Hierarchies('{}')/{}('{}')/Elements/$ref",
            dimension_name, hierarchy_name, subsets, subset_name)
        return self._rest.DELETE(url=url, **kwargs)

    def get_element_names(
            self,
            dimension_name: str,
            hierarchy_name: str,
            subset: Union[str, Subset],
            private: bool = False,
            **kwargs
    ) -> List[str]:
        """
        Retrieve element names from a static or dynamic subset.

        :param dimension_name: Name of the dimension.
        :param hierarchy_name: Name of the hierarchy.
        :param subset: Subset name (str) or Subset object.
        :param private: Whether the subset is private.
        :param kwargs: Additional arguments.
        :return: List of element names.
        """
        if isinstance(subset, str):
            subset = self.get(subset, dimension_name, hierarchy_name, private=private, **kwargs)
        elif not isinstance(subset, Subset):
            raise ValueError(f"subset argument must be of type 'str' or 'Subset', not '{type(subset)}'.")

        if subset.is_static:
            return list(subset.elements)

        from TM1py.Services import ElementService
        element_service = ElementService(self._rest)
        tuples = element_service.execute_set_mdx(
            mdx=subset.expression,
            member_properties=["Name"],
            element_properties=None,
            parent_properties=None,
            **kwargs
        )
        return [entry[0].get("Name", "") for entry in tuples if entry and "Name" in entry[0]]

    def update_static_elements(self, subset: Union[str, Subset], dimension_name: str = None, hierarchy_name: str = None, private: bool = False, elements: Optional[Iterable[Union[str, Element]]] = None,
                               **kwargs) -> Response:
        """
        Replaces elements in a static.
        :param dimension_name: Name of the dimension.
        :param hierarchy_name: Name of the hierarchy.
        :param subset: Subset name (str) or Subset object.
        :param private: Whether the subset is private.
        :param kwargs: Additional arguments.
        :param elements: List of element names (str) or Element objects.
        :return:
        """
        if isinstance(subset, Subset):
            subset_name = subset.name
            if not subset.is_static:
                raise ValueError('Subset must be static.')
            dimension_name = subset.dimension_name
            hierarchy_name = subset.hierarchy_name
        elif isinstance(subset, str):
            subset_name = subset
            if not (dimension_name and hierarchy_name):
                raise ValueError(f"When subset is str, dimension_name and hierarchy_name must also be provided.")
            elif elements is None:
                raise ValueError(f'When subset is str, elements must also be provided.')
        else:
            raise ValueError(f"subset argument must be of type 'str' or 'Subset', not '{type(subset)}'")
        if elements is None:
            elements = subset.elements


        subsets = "PrivateSubsets" if private else "Subsets"
        url = format_url( "/Dimensions('{}')/Hierarchies('{}')/{}('{}')/Elements/$ref", dimension_name, hierarchy_name, subsets, subset_name)

        elements = [element.name if isinstance(element, Element) else element for element in elements]
        elements = [{"@odata.id": f"Dimensions('{dimension_name}')/Hierarchies('{hierarchy_name}')/Elements('{element}')"} for element in elements]

        return self._rest.PUT(url=url, data=json.dumps(elements, ensure_ascii=False), **kwargs)