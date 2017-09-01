# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.Annotation import Annotation
from TM1py.Services.ObjectService import ObjectService


class AnnotationService(ObjectService):
    """ Service to handle Object Updates for TM1 CellAnnotations
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get_all(self, cube_name):
        """ get all annotations from given cube as a List.
    
        :param cube_name:
        :return: list of instances of TM1py.Annotation
        """
        request = "/api/v1/Cubes('{}')/Annotations?$expand=DimensionalContext($select=Name)".format(cube_name)
        response = self._rest.GET(request, '')
        annotations_as_dict = json.loads(response)['value']
        annotations = [Annotation.from_json(json.dumps(element)) for element in annotations_as_dict]
        return annotations

    def create(self, annotation):
        """ create an Annotation
    
            :param annotation: instance of TM1py.Annotation
            :return string: the response
        """
        request = "/api/v1/Annotations"

        payload = collections.OrderedDict()
        payload["Text"] = annotation.text
        payload["ApplicationContext"] = [{"Facet@odata.bind": "ApplicationContextFacets('}Cubes')",
                                          "Value": annotation.object_name}]
        payload["DimensionalContext@odata.bind"] = []
        cube_dimensions_raw = self._rest.GET("/api/v1/Cubes('{}')/Dimensions?$select=Name".format(annotation.object_name))
        cube_dimensions = [dimension['Name'] for dimension in json.loads(cube_dimensions_raw)['value']]
        for dimension, element in zip(cube_dimensions, annotation.dimensional_context):
            payload["DimensionalContext@odata.bind"].append("Dimensions('{}')/Hierarchies('{}')/Members('{}')"
                                                            .format(dimension, dimension, element))
        payload['objectName'] = annotation.object_name
        payload['commentValue'] = annotation.comment_value
        payload['commentType'] = 'ANNOTATION'
        payload['commentLocation'] = ','.join(annotation.dimensional_context)
        response = self._rest.POST(request, json.dumps(payload, ensure_ascii=False))
        return response

    def get(self, annotation_id):
        """ get an annotation from any cube in TM1 Server through its id
    
            :param annotation_id: String, the id of the annotation
    
            :return:
                Annotation: an instance of TM1py.Annoation
        """
        request = "/api/v1/Annotations('{}')?$expand=DimensionalContext($select=Name)".format(annotation_id)
        annotation_as_json = self._rest.GET(request=request)
        return Annotation.from_json(annotation_as_json)

    def update(self, annotation):
        """ update Annotation on TM1 Server
    
            :param annotation: instance of TM1py.Annotation
    
            :Notes:
                updateable attributes:
                    commentValue
        """
        request = "/api/v1/Annotations('{}')".format(annotation.id)
        return self._rest.PATCH(request=request, data=annotation.body)

    def delete(self, annotation_id):
        """ delete Annotation on TM1 Server
    
            :param annotation_id: string, the id of the annotation
    
            :return:
                string: the response
        """
        request = "/api/v1/Annotations('{}')".format(annotation_id)
        return self._rest.DELETE(request=request)
