import configparser
import json
import random
import string
import unittest
from pathlib import Path

from TM1py import Element, Hierarchy, Dimension, Cube
from TM1py.Objects import Annotation
from TM1py.Services import TM1Service


class TestAnnotationMethods(unittest.TestCase):

    @classmethod
    def setup_class(cls):

        # Connection to TM1
        config = configparser.ConfigParser()
        config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**config['tm1srv01'])

        cls.dimension_names = ("TM1py_tests_annotations_dimension1",
                               "TM1py_tests_annotations_dimension2",
                               "TM1py_tests_annotations_dimension3")

        # Build Dimensions
        for dimension_name in cls.dimension_names:
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements)
            dimension = Dimension(dimension_name, [hierarchy])
            cls.tm1.dimensions.update_or_create(dimension)

        # Build Cube
        cls.cube_name = "TM1py_tests_annotations"

        cube = Cube(cls.cube_name, cls.dimension_names)
        cls.tm1.cubes.update_or_create(cube)

        # Adds a single annotation to the cube
        cls.create_annotation()

    @classmethod
    def create_annotation(cls):
        # create annotations
        random_intersection = cls.tm1.cubes.get_random_intersection(cls.cube_name, False)
        random_text = "".join([random.choice(string.printable) for _ in range(100)])

        annotation = Annotation(comment_value=random_text,
                                object_name=cls.cube_name,
                                dimensional_context=random_intersection)
        response = cls.tm1.cubes.annotations.create(annotation)
        annotation_id = response.json()['ID']

        return annotation_id

    @classmethod
    def delete_latest_annotation(cls):
        # get Annotations
        annotations = cls.tm1.cubes.annotations.get_all(cls.cube_name)
        # sort Them
        annotations = sorted(annotations, key=lambda a: str(a.last_updated if a.last_updated else a.created))
        cls.tm1.cubes.annotations.delete(annotations[-1].id)

    def test_create_and_delete_annotation(self):
        # create a random annotation
        annotation_id = self.create_annotation()
        # count existing annotation
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        number_annotations_at_start = len(annotations)
        # delete
        self.tm1.cubes.annotations.delete(annotation_id)
        # count existing annotations
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        number_annotations_at_end = len(annotations)
        # assert
        self.assertEqual(number_annotations_at_start, number_annotations_at_end + 1)

    def test_get_all_annotations_from_cube(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        self.assertGreater(len(annotations), 0)
        for a in annotations:
            b = self.tm1.cubes.annotations.get(a.id)
            self.assertEqual(a.body, b.body)

    def test_update_annotation(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        annotation = annotations[-1]
        # Update Value
        new_random_text = "".join([random.choice(string.printable) for _ in range(100)])
        annotation.comment_value = new_random_text
        response = self.tm1.cubes.annotations.update(annotation)
        annotation_id = json.loads(response.text)['ID']
        a_updated = self.tm1.cubes.annotations.get(annotation_id)
        self.assertEqual(a_updated.comment_value, new_random_text)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cube_name=cls.cube_name)
        for dimension_name in cls.dimension_names:
            cls.tm1.dimensions.delete(dimension_name=dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
