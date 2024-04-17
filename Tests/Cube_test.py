import base64
import unittest

from TM1py import Cube, Rules


class TestCube(unittest.TestCase):

    def setUp(self) -> None:
        self.rules = (
            "['d1':'e1'] = N: 1;\n"
            "['d1':'e2'] = N: 2;\n"
            "['d1':'e3'] = N: 3;\n"
        )
        self.cube = Cube(
            name="c1",
            dimensions=["d1", "d2"],
            rules=self.rules)

    def test_update_rule_with_str(self):
        self.cube.rules = "['d1':'e1'] = N: 1;"

        self.assertEqual(
            self.cube.rules,
            Rules("['d1':'e1'] = N: 1;"))

    def test_update_rule_with_rules_obj(self):
        self.cube.rules = Rules("['d1':'e1'] = N: 2;")

        self.assertEqual(
            self.cube.rules,
            Rules("['d1':'e1'] = N: 2;"))

    def test_disable_rules(self):
        self.cube.disable_rules()

        self.assertEqual(
            "# B64 ENCODED RULES=WydkMSc6J2UxJ10gPSBOOiAxOwpbJ2QxJzonZTInXSA9IE46IDI7ClsnZDEnOidlMyddID0gTjogMzsK",
            self.cube.rules.text
        )

    def test_disable_rules_enable_rules(self):
        original_value = self.cube.rules.text

        self.cube.disable_rules()
        self.cube.enable_rules()

        self.assertEqual(
            original_value,
            self.cube.rules.text
        )

    def test_disable_feeders(self):
        self.cube.rules = Rules(
            "SKIPCHECK;\n"
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            "FEEDERS;\n"
            "['d1':'e2'] => ['d1':'e1'];\n"
            "['d1':'e4'] => ['d1':'e3'];\n"
        )
        self.cube.disable_feeders()

        self.assertEqual(
            "# B64 ENCODED FEEDERS=WydkMSc6J2UyJ10gPT4gWydkMSc6J2UxJ107ClsnZDEnOidlNCddID0+IFsnZDEnOidlMyddOw==",
            self.cube.rules.text.splitlines()[-1]
        )

    def test_disable_feeders_enable_feeders(self):
        self.cube.rules = Rules(
            "SKIPCHECK;\n"
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            "FEEDERS;\n"
            "['d1':'e2'] => ['d1':'e1'];\n"
            "['d1':'e4'] => ['d1':'e3'];"
        )

        original_rules = self.cube.rules.text

        self.cube.disable_feeders()
        self.cube.enable_feeders()

        self.assertEqual(
            original_rules,
            self.cube.rules.text
        )

    def test_enable_rules_disable_rules_with_comments(self):
        self.cube.rules = Rules(
            # Not Relevant
            "SKIPCHECK;\n"
            # Not Relevant
            # Not Relevant
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            # Not Relevant
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            # Not Relevant
            "FEEDERS;\n"
            # Not Relevant
            # Not Relevant
            "['d1':'e2'] => ['d1':'e1'];\n"
            # Not Relevant
            "['d1':'e4'] => ['d1':'e3'];"
        )

        original_rules = self.cube.rules.text

        self.cube.disable_rules()
        self.cube.enable_rules()

        self.assertEqual(
            original_rules,
            self.cube.rules.text
        )

    def test_enable_feeders_disable_feeders_with_comments(self):
        self.cube.rules = Rules(
            # Not Relevant
            "SKIPCHECK;\n"
            # Not Relevant
            # Not Relevant
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            # Not Relevant
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            # Not Relevant
            "FEEDERS;\n"
            # Not Relevant
            # Not Relevant
            "['d1':'e2'] => ['d1':'e1'];\n"
            # Not Relevant
            "['d1':'e4'] => ['d1':'e3'];"
        )

        original_rules = self.cube.rules.text

        self.cube.disable_feeders()
        self.cube.enable_feeders()

        self.assertEqual(
            original_rules,
            self.cube.rules.text
        )

    def test_enable_rules_disable_rules_with_keywords(self):
        self.cube.rules = Rules(
            "FEEDSTRINGS;\n"
            "UNDEVFALS;\n"
            "SKIPCHECK;\n"
            # Not Relevant
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            # Not Relevant
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            "FEEDERS;\n"
            "['d1':'e2'] => ['d1':'e1'];\n"
            "['d1':'e4'] => ['d1':'e3'];"
        )

        original_rules = self.cube.rules.text

        self.cube.disable_rules()
        self.cube.enable_rules()

        self.assertEqual(
            original_rules,
            self.cube.rules.text
        )

    def test_enable_feeders_disable_feeders_with_keywords(self):
        self.cube.rules = Rules(
            "FEEDSTRINGS;\n"
            "UNDEVFALS;\n"
            "SKIPCHECK;\n"
            # Not Relevant
            "['d1':'e1'] = N: ['d1':'e2'] * 2;\n"
            # Not Relevant
            "['d1':'e3'] = N: ['d1':'e4'] * 2;\n"
            "FEEDERS;\n"
            "['d1':'e2'] => ['d1':'e1'];\n"
            "['d1':'e4'] => ['d1':'e3'];"
        )

        original_rules = self.cube.rules.text

        self.cube.disable_feeders()
        self.cube.enable_feeders()

        self.assertEqual(
            original_rules,
            self.cube.rules.text
        )


if __name__ == '__main__':
    unittest.main()
