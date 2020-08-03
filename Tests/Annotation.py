import configparser
import random
import string
import unittest
from pathlib import Path

from TM1py import Cube, Dimension, Element, Hierarchy
from TM1py.Objects import Annotation
from TM1py.Services import TM1Service


class TestAnnotationMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

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

    @classmethod
    def setUp(self):

        random_intersection = self.tm1.cubes.get_random_intersection(self.cube_name, False)
        random_text = "".join([random.choice(string.printable) for _ in range(100)])

        annotation = Annotation(comment_value=random_text,
                                object_name=self.cube_name,
                                dimensional_context=random_intersection)
        
        self.annotation_id = self.tm1.cubes.annotations.create(annotation).json().get("ID")

    @classmethod
    def tearDown(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        
        for a in annotations:
            if a.id == self.annotation_id:
                self.tm1.annotations.delete(self.annotation_id)
            

    def test_get_all(self):
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        self.assertGreater(len(annotations), 0)

    def test_create(self):
        annotation_count = len(self.tm1.cubes.annotations.get_all(self.cube_name))
        
        random_intersection = self.tm1.cubes.get_random_intersection(self.cube_name, False)
        random_text = "".join([random.choice(string.printable) for _ in range(100)])

        annotation = Annotation(comment_value=random_text,
                                object_name=self.cube_name,
                                dimensional_context=random_intersection)

        self.tm1.annotations.create(annotation)

        self.assertGreater(len(self.tm1.cubes.annotations.get_all(self.cube_name)), annotation_count)
        

    def test_get(self):
        annotation = self.tm1.cubes.annotations.get(self.annotation_id)
        self.assertEqual(annotation.id, self.annotation_id)

    def test_update(self):
        annotation = self.tm1.cubes.annotations.get(self.annotation_id)  
        new_random_text = "".join([random.choice(string.printable) for _ in range(100)])
        annotation.comment_value = new_random_text

        self.tm1.cubes.annotations.update(annotation)
        annotation_updated = self.tm1.cubes.annotations.get(self.annotation_id)
        self.assertEqual(annotation_updated.comment_value, new_random_text)
        self.assertNotEqual(annotation_updated.last_updated, annotation.last_updated)

    def test_delete(self):
        annotation_id = self.tm1.cubes.annotations.get(self.annotation_id).id  
        annotation_count = len(self.tm1.cubes.annotations.get_all(self.cube_name))
        self.tm1.annotations.delete(annotation_id)
        self.assertLess(len(self.tm1.cubes.annotations.get_all(self.cube_name)), annotation_count)


    @classmethod
    def tearDownClass(cls):
        cls.tm1.cubes.delete(cube_name=cls.cube_name)
        for dimension_name in cls.dimension_names:
            cls.tm1.dimensions.delete(dimension_name=dimension_name)
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
