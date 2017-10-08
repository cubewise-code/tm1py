import json
import random
import string
import unittest


from TM1py.Services import TM1Service
from TM1py.Objects import Annotation

from Tests.config import test_config

# hard stuff for this test


class TestAnnotationMethods(unittest.TestCase):
    tm1 = TM1Service(**test_config)

    # Get Random Cube + Intersection
    all_cube_names = tm1.cubes.get_all_names()
    cube_name = random.choice(all_cube_names)
    
    random_intersection = tm1.cubes.get_random_intersection(cube_name, False)
    random_text = "".join([random.choice(string.printable) for i in range(100)])

    def test1_create_annotation(self):
        annotation = Annotation(comment_value=self.random_text,
                                object_name=self.cube_name,
                                dimensional_context=self.random_intersection)
        response = self.tm1.cubes.annotations.create(annotation)
        annotation_id = json.loads(response)['ID']

        # test, if it exists
        all_annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        if len(all_annotations) > 0:
            annotation = self.tm1.cubes.annotations.get(annotation_id)
            self.assertEqual(self.random_text, annotation.comment_value)

    def test2_get_all_annotations_from_cube(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        for a in annotations:
            b = self.tm1.cubes.annotations.get(a.id)
            self.assertEqual(a.body, b.body)

    def test3_update_annotation(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        for a in annotations:
            # Get the anntoation that was created in test1
            if a.dimensional_context == self.random_intersection and a.comment_value == self.random_text:
                # Update Value and Coordinates
                new_random_text = "".join([random.choice(string.printable) for _ in range(100)])
                a.comment_value = new_random_text
                response = self.tm1.cubes.annotations.update(a)
                annotation_id = json.loads(response)['ID']
                a_updated = self.tm1.cubes.annotations.get(annotation_id)
                self.assertEqual(a_updated.comment_value, new_random_text)

    def test4_delete_annotation(self):
        # get Annotations
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        # sort Them
        annotations = sorted(annotations, key=lambda a: str(a.last_updated if a.last_updated else a.created))
        # First count
        number_annotations_at_start = len(annotations)

        last_annotation = annotations[-1]
        self.tm1.cubes.annotations.delete(last_annotation._id)

        # get Annotations again
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        # Second count
        number_annotations_at_end = len(annotations)

        self.assertEqual(number_annotations_at_start, number_annotations_at_end + 1)
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
