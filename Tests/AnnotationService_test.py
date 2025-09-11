import configparser
import random
import string
import unittest
from pathlib import Path
from uuid import uuid1

from TM1py.Objects import Annotation, Cube, Dimension, Element, Hierarchy
from TM1py.Services import TM1Service


class TestAnnotationService(unittest.TestCase):
    tm1: TM1Service

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

    @classmethod
    def tearDownClass(cls):
        """
        Close the connection once all tests have run.
        """
        cls.tm1.logout()

    def setUp(self):
        """
        Run before each test to create a cube with test annotations
        """
        # Build Dimensions
        test_uuid = str(uuid1()).replace("-", "_")
        self.dimension_names = (
            "TM1py_tests_annotations_dimension1_" + test_uuid,
            "TM1py_tests_annotations_dimension2_" + test_uuid,
            "TM1py_tests_annotations_dimension3_" + test_uuid,
        )

        for dimension_name in self.dimension_names:
            elements = [Element("Element {}".format(str(j)), "Numeric") for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_name=dimension_name, name=dimension_name, elements=elements)
            dimension = Dimension(dimension_name, [hierarchy])
            self.tm1.dimensions.update_or_create(dimension)

        # Build Cube
        self.cube_name = "TM1py_tests_annotations_" + test_uuid
        cube = Cube(self.cube_name, self.dimension_names)
        self.tm1.cubes.update_or_create(cube)

        random_intersection = self.tm1.cubes.get_random_intersection(self.cube_name, False)
        random_text = "".join([random.choice(string.printable) for _ in range(100)])

        annotation = Annotation(
            comment_value=random_text, object_name=self.cube_name, dimensional_context=random_intersection
        )

        self.annotation_id = self.tm1.cubes.annotations.create(annotation).json().get("ID")

    def tearDown(self):
        """
        Run at the end of each test to remove unique test cube and dimensions.
        Created annotations will be deleted implicitly by removing the cube.
        """
        self.tm1.cubes.delete(cube_name=self.cube_name)

        for dimension_name in self.dimension_names:
            self.tm1.dimensions.delete(dimension_name=dimension_name)

    def test_get_all(self):
        """
        Check that get_all returns a list
        Check that the list of annotations returned contains the test annotation
        """
        annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        self.assertIsInstance(annotations, list)

        annotation_ids = [a.id for a in annotations]
        self.assertIn(self.annotation_id, annotation_ids)

    def test_create(self):
        """
        Check that an annotation can be created on the server
        Check that created annotation has the correct comment_value
        """
        annotation_count = len(self.tm1.cubes.annotations.get_all(self.cube_name))
        random_intersection = self.tm1.cubes.get_random_intersection(self.cube_name, False)
        random_text = "".join([random.choice(string.printable) for _ in range(100)])

        annotation = Annotation(
            comment_value=random_text, object_name=self.cube_name, dimensional_context=random_intersection
        )

        annotation_id = self.tm1.cubes.annotations.create(annotation).json().get("ID")
        all_annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        self.assertGreater(len(all_annotations), annotation_count)

        new_annotation = self.tm1.cubes.annotations.get(annotation_id)
        self.assertEqual(new_annotation.comment_value, random_text)

    def test_create_many(self):
        """
        Check that an annotation can be created on the server
        Check that created annotation has the correct comment_value
        """
        pre_annotation_count = len(self.tm1.cubes.annotations.get_all(self.cube_name))

        annotations = list()
        for _ in range(5):
            random_intersection = self.tm1.cubes.get_random_intersection(self.cube_name, False)
            random_text = "".join([random.choice(string.printable) for _ in range(100)])

            annotations.append(
                Annotation(
                    comment_value=random_text, object_name=self.cube_name, dimensional_context=random_intersection
                )
            )

        self.tm1.cubes.annotations.create_many(annotations)
        all_annotations = self.tm1.cubes.annotations.get_all(self.cube_name)
        self.assertEqual(len(all_annotations), pre_annotation_count + 5)

    def test_get(self):
        """
        Check that get returns the test annotation from its id
        """
        annotation = self.tm1.cubes.annotations.get(self.annotation_id)
        self.assertEqual(annotation.id, self.annotation_id)

    def test_update(self):
        """
        Check that the test annotation's comment_value can be changed
        Check that the last_updated date has increased
        Check that the created date remains the same
        """
        annotation = self.tm1.cubes.annotations.get(self.annotation_id)
        new_random_text = "".join([random.choice(string.printable) for _ in range(100)])
        annotation.comment_value = new_random_text

        self.tm1.cubes.annotations.update(annotation)
        annotation_updated = self.tm1.cubes.annotations.get(self.annotation_id)

        self.assertEqual(annotation_updated.comment_value, new_random_text)
        self.assertNotEqual(annotation_updated.last_updated, annotation.last_updated)
        self.assertEqual(annotation_updated.created, annotation.created)

    def test_delete(self):
        """
        Check that the test annotation can be deleted
        """

        annotation_id = self.annotation_id
        annotation_count = len(self.tm1.cubes.annotations.get_all(self.cube_name))
        self.tm1.annotations.delete(annotation_id)
        self.assertLess(len(self.tm1.cubes.annotations.get_all(self.cube_name)), annotation_count)


if __name__ == "__main__":
    unittest.main()
