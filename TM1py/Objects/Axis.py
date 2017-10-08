# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.Subset import Subset, AnonymousSubset

from TM1py.Objects.TM1Object import TM1Object


class ViewAxisSelection(TM1Object):
    """ Describes what is selected in a dimension on an axis. Can be a Registered Subset or an Anonymous Subset

    """
    def __init__(self, dimension_name, subset):
        """
            :Parameters:
                `dimension_name` : String
                `subset` : Subset or AnonymousSubset
        """
        self._subset = subset
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name

    @property
    def body(self):
        return json.dumps(self._construct_body(), ensure_ascii=False)

    @property
    def body_as_dict(self):
        return self._construct_body()

    def _construct_body(self):
        """ construct the ODATA conform JSON represenation for the ViewAxisSelection entity.

        :return: dictionary
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            path = 'Dimensions(\'{}\')/Hierarchies(\'{}\')/Subsets(\'{}\')'.format(
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = path
        return body_as_dict


class ViewTitleSelection:
    """ Describes what is selected in a dimension on the view title.
        Can be a Registered Subset or an Anonymous Subset

    """
    def __init__(self, dimension_name, subset, selected):
        self._dimension_name = dimension_name
        self._hierarchy_name = dimension_name
        self._subset = subset
        self._selected = selected

    @property
    def body(self):
        return json.dumps(self._construct_body(), ensure_ascii=False)

    def _construct_body(self):
        """ construct the ODATA conform JSON represenation for the ViewTitleSelection entity.

        :return: string, the valid JSON
        """
        body_as_dict = collections.OrderedDict()
        if isinstance(self._subset, AnonymousSubset):
            body_as_dict['Subset'] = json.loads(self._subset.body)
        elif isinstance(self._subset, Subset):
            path = "Dimensions('{}')/Hierarchies('{}')/Subsets('{}')".format(
                self._dimension_name, self._hierarchy_name, self._subset.name)
            body_as_dict['Subset@odata.bind'] = path
        selected = "Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
            self._dimension_name, self._hierarchy_name, self._selected)
        body_as_dict['Selected@odata.bind'] = selected
        return body_as_dict
