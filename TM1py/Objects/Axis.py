# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, Union

from TM1py.Objects.Subset import Subset, AnonymousSubset
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class ViewAxisSelection(TM1Object):
    """ Describes what is selected in a dimension on an axis. Can be a Registered Subset or an Anonymous Subset

    """

    def __init__(self, dimension_name: str, subset: Union[Subset, AnonymousSubset]):
        """
            :Parameters:
                `dimension_name` : String
                `subset` : Subset or AnonymousSubset
        """
        self._subset = subset
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name

    @property
    def subset(self) -> Union[Subset, AnonymousSubset]:
        """
        Return the set of subset.

        Args:
            self: (todo): write your description
        """
        return self._subset

    @property
    def dimension_name(self) -> str:
        """
        Return the name of the dimension.

        Args:
            self: (todo): write your description
        """
        return self._dimension_name

    @property
    def hierarchy_name(self) -> str:
        """
        Returns the hierarchy name.

        Args:
            self: (todo): write your description
        """
        return self._hierarchy_name

    @property
    def body(self) -> str:
        """
        Return the body of the message.

        Args:
            self: (todo): write your description
        """
        return json.dumps(self._construct_body(), ensure_ascii=False)

    @property
    def body_as_dict(self) -> Dict:
        """
        Return the body as a dictionary.

        Args:
            self: (todo): write your description
        """
        return self._construct_body()

    def _construct_body(self) -> Dict:
        """ construct the ODATA conform JSON represenation for the ViewAxisSelection entity.

        :return: dictionary
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            subset_path = format_url(
                "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')",
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = subset_path
        return body_as_dict


class ViewTitleSelection:
    """ Describes what is selected in a dimension on the view title.
        Can be a Registered Subset or an Anonymous Subset

    """

    def __init__(self, dimension_name: str, subset: Union[AnonymousSubset, Subset], selected: str):
        """
        Init a new subset.

        Args:
            self: (todo): write your description
            dimension_name: (str): write your description
            subset: (todo): write your description
            selected: (str): write your description
        """
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name
        self._subset = subset
        self._selected = selected

    @property
    def subset(self) -> Union[Subset, AnonymousSubset]:
        """
        Return the set of subset.

        Args:
            self: (todo): write your description
        """
        return self._subset

    @property
    def dimension_name(self) -> str:
        """
        Return the name of the dimension.

        Args:
            self: (todo): write your description
        """
        return self._dimension_name

    @property
    def hierarchy_name(self) -> str:
        """
        Returns the hierarchy name.

        Args:
            self: (todo): write your description
        """
        return self._hierarchy_name

    @property
    def selected(self) -> str:
        """
        Returns the selected item.

        Args:
            self: (todo): write your description
        """
        return self._selected

    @property
    def body(self) -> str:
        """
        Return the body of the message.

        Args:
            self: (todo): write your description
        """
        return json.dumps(self._construct_body(), ensure_ascii=False)

    def _construct_body(self) -> Dict:
        """ construct the ODATA conform JSON represenation for the ViewTitleSelection entity.

        :return: string, the valid JSON
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            subset_path = format_url(
                "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')",
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = subset_path
        element_path = format_url(
            "Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            self._dimension_name, self._hierarchy_name, self._selected)
        body_as_dict['Selected@odata.bind'] = element_path
        return body_as_dict
