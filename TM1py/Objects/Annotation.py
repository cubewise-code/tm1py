# -*- coding: utf-8 -*-

import json
import collections

from TM1py.Objects.TM1Object import TM1Object


class Annotation(TM1Object):
    """ Abtraction of TM1 Annotation

        :Notes:
            - Class complete, functional and tested.
            - doesn't cover Attachments though
    """
    def __init__(self, comment_value, object_name, dimensional_context, comment_type='ANNOTATION', annotation_id=None,
                 text='', creator=None, created=None, last_updated_by=None, last_updated=None):
        self._id = annotation_id
        self._text = text
        self._creator = creator
        self._created = created
        self._last_updated_by = last_updated_by
        self._last_updated = last_updated
        self._dimensional_context = dimensional_context
        self._comment_type = comment_type
        self._comment_value = comment_value
        self._object_name = object_name

    @classmethod
    def from_json(cls, annotation_as_json):
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
    def body(self):
        return self._construct_body()

    @property
    def comment_value(self):
        return self._comment_value

    @property
    def text(self):
        return self._text

    @property
    def dimensional_context(self):
        return self._dimensional_context

    @property
    def created(self):
        return self._created

    @property
    def object_name(self):
        return self._object_name

    @property
    def last_updated(self):
        return self._last_updated

    @property
    def last_updated_by(self):
        return self._last_updated_by

    @comment_value.setter
    def comment_value(self, value):
        self._comment_value = value

    @property
    def id(self):
        return self._id

    def move(self, dimension_order, dimension, target_element, source_element=None):
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

    def _construct_body(self):
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
