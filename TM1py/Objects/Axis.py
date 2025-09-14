# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, Union

from TM1py.Objects.Subset import AnonymousSubset, Subset
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class ViewAxisSelection(TM1Object):
    """Describes what is selected in a dimension on an axis. Can be a Registered Subset or an Anonymous Subset"""

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
        return self._subset

    @property
    def dimension_name(self) -> str:
        return self._dimension_name

    @property
    def hierarchy_name(self) -> str:
        return self._hierarchy_name

    @property
    def body(self) -> str:
        return json.dumps(self._construct_body(), ensure_ascii=False)

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    def _construct_body(self) -> Dict:
        """construct the ODATA conform JSON represenation for the ViewAxisSelection entity.

        :return: dictionary
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict["Subset"] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            subset_path = format_url(
                "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')",
                self._dimension_name,
                self._hierarchy_name,
                self._subset.name,
            )
            body_as_dict["Subset@odata.bind"] = subset_path
        return body_as_dict


class ViewTitleSelection:
    """Describes what is selected in a dimension on the view title.
    Can be a Registered Subset or an Anonymous Subset

    """

    def __init__(self, dimension_name: str, subset: Union[AnonymousSubset, Subset], selected: str):
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name
        self._subset = subset
        self._selected = selected

    @property
    def subset(self) -> Union[Subset, AnonymousSubset]:
        return self._subset

    @property
    def dimension_name(self) -> str:
        return self._dimension_name

    @property
    def hierarchy_name(self) -> str:
        return self._hierarchy_name

    @property
    def selected(self) -> str:
        return self._selected

    @property
    def body(self) -> str:
        return json.dumps(self._construct_body(), ensure_ascii=False)

    def _construct_body(self) -> Dict:
        """construct the ODATA conform JSON represenation for the ViewTitleSelection entity.

        :return: string, the valid JSON
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict["Subset"] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            subset_path = format_url(
                "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')",
                self._dimension_name,
                self._hierarchy_name,
                self._subset.name,
            )
            body_as_dict["Subset@odata.bind"] = subset_path
        element_path = format_url(
            "Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            self._dimension_name,
            self._hierarchy_name,
            self._selected,
        )
        body_as_dict["Selected@odata.bind"] = element_path
        return body_as_dict
