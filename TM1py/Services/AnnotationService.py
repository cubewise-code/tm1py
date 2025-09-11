# -*- coding: utf-8 -*-

import json
from typing import List, Iterable

from requests import Response

from TM1py.Objects.Annotation import Annotation
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url, CaseAndSpaceInsensitiveDict


class AnnotationService(ObjectService):
    """Service to handle Object Updates for TM1 CellAnnotations"""

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get_all(self, cube_name: str, **kwargs) -> List[Annotation]:
        """get all annotations from given cube as a List.

        :param cube_name:
        """
        url = format_url("/Cubes('{}')/Annotations?$expand=DimensionalContext($select=Name)", cube_name)
        response = self._rest.GET(url, **kwargs)

        annotations_as_dict = response.json()["value"]
        annotations = [Annotation.from_json(json.dumps(element)) for element in annotations_as_dict]
        return annotations

    def create(self, annotation: Annotation, **kwargs) -> Response:
        """create an Annotation

        :param annotation: instance of TM1py.Annotation
        """
        url = "/Annotations"

        from TM1py import CubeService

        cube_dimensions = CubeService(self._rest).get_dimension_names(
            cube_name=annotation.object_name, skip_sandbox_dimension=True
        )

        response = self._rest.POST(url, json.dumps(annotation.construct_body_for_post(cube_dimensions)), **kwargs)
        return response

    def create_many(self, annotations: Iterable[Annotation], **kwargs) -> Response:
        """create an Annotation

        :param annotations: instances of TM1py.Annotation
        """
        payload = list()
        cube_dimensions = CaseAndSpaceInsensitiveDict()

        for annotation in annotations:
            dimension_names = cube_dimensions.get(annotation.object_name, None)
            if not dimension_names:
                from TM1py import CubeService

                dimension_names = CubeService(self._rest).get_dimension_names(
                    cube_name=annotation.object_name, skip_sandbox_dimension=True
                )

                cube_dimensions[annotation.object_name] = dimension_names
            payload.append(annotation.construct_body_for_post(dimension_names))

        response = self._rest.POST("/Annotations", json.dumps(payload), **kwargs)

        return response

    def get(self, annotation_id: str, **kwargs) -> Annotation:
        """get an annotation from any cube through its unique id

        :param annotation_id: String, the id of the annotation
        """
        request = format_url("/Annotations('{}')?$expand=DimensionalContext($select=Name)", annotation_id)
        response = self._rest.GET(url=request, **kwargs)
        return Annotation.from_json(response.text)

    def update(self, annotation: Annotation, **kwargs) -> Response:
        """update Annotation.
        updateable attributes: commentValue

        :param annotation: instance of TM1py.Annotation
        """
        url = format_url("/Annotations('{}')", annotation.id)
        return self._rest.PATCH(url=url, data=annotation.body, **kwargs)

    def delete(self, annotation_id: str, **kwargs) -> Response:
        """delete Annotation

        :param annotation_id: string, the id of the annotation
        """
        url = format_url("/Annotations('{}')", annotation_id)
        return self._rest.DELETE(url=url, **kwargs)
