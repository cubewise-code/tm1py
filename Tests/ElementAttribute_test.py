import unittest

from TM1py import ElementAttribute


class TestElementAttribute(unittest.TestCase):

    def test_eq_happy_case(self):
        element_attribute1 = ElementAttribute(name="Attribute 1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute 1", attribute_type="String")

        self.assertEqual(element_attribute1, element_attribute2)

    def test_ne_name(self):
        element_attribute1 = ElementAttribute(name="Attribute 1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute 2", attribute_type="String")

        self.assertNotEqual(element_attribute1, element_attribute2)

    def test_ne_type(self):
        element_attribute1 = ElementAttribute(name="Attribute 1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute 1", attribute_type="Numeric")

        self.assertNotEqual(element_attribute1, element_attribute2)

    def test_eq_case_space_difference(self):
        element_attribute1 = ElementAttribute(name="Attribute 1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="ATTRIBUTE1", attribute_type="String")

        self.assertEqual(element_attribute1, element_attribute2)

    def test_hash_happy_case(self):
        element_attribute1 = ElementAttribute(name="Attribute 1", attribute_type="String")
        element_attribute2 = ElementAttribute(name="Attribute 1", attribute_type="String")

        self.assertEqual(hash(element_attribute1), hash(element_attribute2))

    def test_construct_body(self):
        element = ElementAttribute(name="Attribute 1", attribute_type="Numeric")

        self.assertEqual(
            element.body_as_dict,
            {'Name': 'Attribute 1', 'Type': 'Numeric'})


if __name__ == '__main__':
    unittest.main()
