import json
import unittest
import random
import string

from Services.AnnotationService import AnnotationService
from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.DataService import DataService
from Objects.Annotation import Annotation


# Configuration for tests
port = 8001
user = 'admin'
pwd = 'apple'
cube_name = 'Plan_BudgetPlan'


class TestAnnotationMethods(unittest.TestCase):
    login = LoginService.native(user, pwd)
    tm1_rest = RESTService(ip='', port=port, login=login, ssl=False)

    annotation_service = AnnotationService(tm1_rest)
    data_service = DataService(tm1_rest)

    # Get Random Cube + Intersection
    random_intersection = data_service.get_random_intersection(cube_name, False)
    random_text = "".join([random.choice(string.printable) for i in range(100)])

    def test1_create_annotation(self):
        annotation = Annotation(comment_value=self.random_text,
                                object_name=cube_name,
                                dimensional_context=self.random_intersection)
        response = self.annotation_service.create(annotation)
        annotation_id = json.loads(response)['ID']

        # test, if it exists
        all_annotations = self.annotation_service.get_all(cube_name)
        if len(all_annotations) > 0:
            annotation = self.annotation_service.get(annotation_id)
            self.assertEqual(self.random_text, annotation.comment_value)

    def test2_get_all_annotations_from_cube(self):
        annotations = self.annotation_service.get_all(cube_name)
        for a in annotations:
            b = self.annotation_service.get(a.id)
            self.assertEqual(a.body, b.body)

    def test3_update_annotation(self):
        annotations = self.annotation_service.get_all(cube_name)
        for a in annotations:
            # Get the anntoation that was created in test1
            if a.dimensional_context == self.random_intersection and a.comment_value == self.random_text:
                # Update Value and Coordinates
                new_random_text = "".join([random.choice(string.printable) for _ in range(100)])
                a.comment_value = new_random_text
                response = self.annotation_service.update(a)
                annotation_id = json.loads(response)['ID']
                a_updated = self.annotation_service.get(annotation_id)
                self.assertEqual(a_updated.comment_value, new_random_text)

    def test4_delete_annotation(self):
        # get Annotations
        annotations = self.annotation_service.get_all(cube_name)
        # sort Them
        annotations = sorted(annotations, key=lambda a: str(a.last_updated if a.last_updated else a.created))
        # First count
        number_annotations_at_start = len(annotations)

        last_annotation = annotations[-1]
        self.annotation_service.delete(last_annotation._id)

        # get Annotations again
        annotations = self.annotation_service.get_all(cube_name)
        # Second count
        number_annotations_at_end = len(annotations)

        self.assertEqual(number_annotations_at_start, number_annotations_at_end + 1)
        self.tm1_rest.logout()

if __name__ == '__main__':
    unittest.main()
