from TM1py import TM1Queries, Annotation
import uuid
import json
import unittest


class TestAnnotationMethods(unittest.TestCase):
    q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)

    def test1_get_all_annotations_from_cube(self):
        annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
        for annotation in annotations:
            self.assertIsInstance(annotation, Annotation)

    def test2_get_annotation(self):
        all_annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
        if len(all_annotations) > 0:
            first_annotation = all_annotations[0]
            annotation_id = first_annotation._id
            annotation = self.q.get_annotation(annotation_id)
            self.assertIsInstance(annotation, Annotation)

    def test3_update_annotation(self):
        all_annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
        if len(all_annotations) > 0:
            first_annotation = all_annotations[0]
            random_string = str(uuid.uuid4())
            first_annotation._comment_value = random_string
            response = self.q.update_annotation(first_annotation)
            self.assertIn(random_string, response)

    def test4_create_annotation(self):
        all_annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
        if len(all_annotations) > 1:
            second_annotation = all_annotations[1]
            response = self.q.create_annotation(second_annotation)
            created_annotation = json.loads(response)

            annotation_id = created_annotation['ID']
            annotation = self.q.get_annotation(annotation_id)

            self.assertIsInstance(annotation, Annotation)

    def test5_delete_annotation(self):
        annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
        if len(annotations) > 0:
            number_annotations_at_start = len(annotations)

            last_annotation = annotations[-1]
            self.q.delete_annotation(last_annotation._id)

            annotations = self.q.get_all_annotations_from_cube('plan_BudgetPlan')
            number_annotations_at_end = len(annotations)

            self.assertEqual(number_annotations_at_start, number_annotations_at_end + 1)


if __name__ == '__main__':
    unittest.main()
