import unittest

from TM1py import Cube, Rules


class TestCube(unittest.TestCase):
    rules = """
['d1':'e1'] = N: 1;
['d1':'e2'] = N: 2;
['d1':'e3'] = N: 3;
"""
    cube = Cube(name="c1", dimensions=["d1", "d2"], rules=rules)

    def test_update_rule_with_str(self):
        self.cube.rules = "['d1':'e1'] = N: 1;"

        self.assertEqual(self.cube.rules, Rules("['d1':'e1'] = N: 1;"))

    def test_update_rule_with_rules_obj(self):
        self.cube.rules = Rules("['d1':'e1'] = N: 2;")

        self.assertEqual(self.cube.rules, Rules("['d1':'e1'] = N: 2;"))


if __name__ == "__main__":
    unittest.main()
