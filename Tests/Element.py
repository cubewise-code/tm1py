import unittest

from TM1py import Element


class TestElement(unittest.TestCase):

    def test_eq_happy_case(self):
        element1 = Element(name="Element 1", element_type="Numeric")
        element2 = Element(name="Element 1", element_type="NUMERIC")

        self.assertEqual(element1, element2)

    def test_ne_happy_case(self):
        element1 = Element(name="Element 1", element_type="Numeric")
        element2 = Element(name="Element 2", element_type="NUMERIC")

        self.assertNotEqual(element1, element2)

    def test_eq_case_space_difference(self):
        element1 = Element(name="Element 1", element_type="Numeric")
        element2 = Element(name="ELEMENT1", element_type="NUMERIC")

        self.assertEqual(element1, element2)

    def test_hash_happy_case(self):
        element1 = Element(name="Element 1", element_type="Numeric")
        element2 = Element(name="Element 1", element_type="Numeric")

        self.assertEqual(hash(element1), hash(element2))

    def test_construct_body(self):
        element = Element("e1", "Numeric")

        self.assertEqual(
            element._construct_body(),
            {'Name': 'e1', 'Type': 'Numeric'})


if __name__ == '__main__':
    unittest.main()
