# -*- coding: utf-8 -*-

import collections
import json
from typing import Iterable, Dict, List

from TM1py.Objects.TM1Object import TM1Object


class Annotation(TM1Object):
    """ Abtraction of TM1 Annotation

        :Notes:
            - Class complete, functional and tested.
            - doesn't cover Attachments though
    """

    def __init__(self, comment_value: str, object_name: str, dimensional_context: Iterable[str],
                 comment_type: str = 'ANNOTATION', annotation_id: str = None,
                 text: str = '', creator: str = None, created: str = None, last_updated_by: str = None,
                 last_updated: str = None):
        """
        Initialize a comment.

        Args:
            self: (todo): write your description
            comment_value: (str): write your description
            object_name: (str): write your description
            dimensional_context: (int): write your description
            comment_type: (str): write your description
            annotation_id: (str): write your description
            text: (str): write your description
            creator: (todo): write your description
            created: (todo): write your description
            last_updated_by: (str): write your description
            last_updated: (todo): write your description
        """
        self._id = annotation_id
        self._text = text
        self._creator = creator
        self._created = created
        self._last_updated_by = last_updated_by
        self._last_updated = last_updated
        self._dimensional_context = list(dimensional_context)
        self._comment_type = comment_type
        self._comment_value = comment_value
        self._object_name = object_name

    @classmethod
    def from_json(cls, annotation_as_json: str) -> 'Annotation':
        """ Alternative constructor

            :param annotation_as_json: String, JSON
            :return: instance of TM1py.Process
        """
        annotation_as_dict = json.loads(annotation_as_json)
        annotation_id = annotation_as_dict['ID']
        text = annotation_as_dict['Text']
        creator = annotation_as_dict['Creator']
        created = annotation_as_dict['Created']
        last_updated_by = annotation_as_dict['LastUpdatedBy']
        last_updated = annotation_as_dict['LastUpdated']
        dimensional_context = [item['Name'] for item in annotation_as_dict['DimensionalContext']]
        comment_type = annotation_as_dict['commentType']
        comment_value = annotation_as_dict['commentValue']
        object_name = annotation_as_dict['objectName']
        return cls(comment_value=comment_value, object_name=object_name, dimensional_context=dimensional_context,
                   comment_type=comment_type, annotation_id=annotation_id, text=text, creator=creator, created=created,
                   last_updated_by=last_updated_by, last_updated=last_updated)

    @property
    def body(self) -> str:
        """
        Return the body of the request.

        Args:
            self: (todo): write your description
        """
        return self._construct_body()

    @property
    def comment_value(self) -> str:
        """
        Return the comment value.

        Args:
            self: (todo): write your description
        """
        return self._comment_value

    @property
    def text(self) -> str:
        """
        Return the text.

        Args:
            self: (todo): write your description
        """
        return self._text

    @property
    def dimensional_context(self) -> List[str]:
        """
        Return the current : class.

        Args:
            self: (todo): write your description
        """
        return self._dimensional_context

    @property
    def created(self) -> str:
        """
        Returns the created : class.

        Args:
            self: (todo): write your description
        """
        return self._created

    @property
    def object_name(self) -> str:
        """
        Returns the name of the object.

        Args:
            self: (todo): write your description
        """
        return self._object_name

    @property
    def last_updated(self) -> str:
        """
        Returns the last changes.

        Args:
            self: (todo): write your description
        """
        return self._last_updated

    @property
    def last_updated_by(self) -> str:
        """
        Returns the last updated changes.

        Args:
            self: (todo): write your description
        """
        return self._last_updated_by

    @comment_value.setter
    def comment_value(self, value: str):
        """
        Set the comment value.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._comment_value = value

    @property
    def id(self) -> str:
        """
        Returns the id of the entity.

        Args:
            self: (todo): write your description
        """
        return self._id

    def move(self, dimension_order: Iterable[str], dimension: str, target_element: str, source_element: str = None):
        """ Move annotation on given dimension from source_element to target_element
        
            :param dimension_order: List, order of the dimensions in the cube
            :param dimension: dimension name
            :param target_element: target element name
            :param source_element:  source element name
            :return: 
        """
        for i, dimension_name in enumerate(dimension_order):
            if dimension_name.lower() == dimension.lower():
                if not source_element or self._dimensional_context[i] == source_element:
                    self._dimensional_context[i] = target_element

    def _construct_body(self) -> str:
        """ construct the ODATA conform JSON represenation for the Annotation entity.

            :return: string, the valid JSON
        """
        dimensional_context = [{'Name': element} for element in self._dimensional_context]
        body = collections.OrderedDict()
        body['ID'] = self._id
        body['Text'] = self._text
        body['Creator'] = self._creator
        body['Created'] = self._created
        body['LastUpdatedBy'] = self._last_updated_by
        body['LastUpdated'] = self._last_updated
        body['DimensionalContext'] = dimensional_context
        comment_locations = ','.join(self._dimensional_context)
        body['commentLocation'] = comment_locations[1:]
        body['commentType'] = self._comment_type
        body['commentValue'] = self._comment_value
        body['objectName'] = self._object_name
        return json.dumps(body, ensure_ascii=False)
