import unittest

from TM1py.Objects import Sandbox


class TestSandboxMethods(unittest.TestCase):

    def test_body_include_in_sandbox_dimension_true(self):
        sandbox = Sandbox("sandbox", True)

        self.assertEqual(
            '{"Name": "sandbox", "IncludeInSandboxDimension": true}',
            sandbox.body)

    def test_body_include_in_sandbox_dimension_false(self):
        sandbox = Sandbox("sandbox", False)

        self.assertEqual(
            '{"Name": "sandbox", "IncludeInSandboxDimension": false}',
            sandbox.body)

    def test_from_json_include_in_sandbox_dimension_true(self):
        sandbox = Sandbox.from_dict({
            "Name": "sandbox",
            "IncludeInSandboxDimension": True,
            "IsLoaded": True,
            "IsActive": False,
            "IsQueued": False})

        self.assertEqual(sandbox.name, "sandbox")
        self.assertTrue(sandbox._include_in_sandbox_dimension)

    def test_from_json_include_in_sandbox_dimension_false(self):
        sandbox = Sandbox.from_dict({
            "Name": "sandbox",
            "IncludeInSandboxDimension": False,
            "IsLoaded": True,
            "IsActive": False,
            "IsQueued": False})

        self.assertEqual(sandbox.name, "sandbox")
        self.assertFalse(sandbox._include_in_sandbox_dimension)

    def test_change_name(self):
        sandbox = Sandbox("sandbox", True)
        sandbox.name = "new sandbox"

        self.assertEqual(
            '{"Name": "new sandbox", "IncludeInSandboxDimension": true}',
            sandbox.body)

    def test_change_include_in_sandbox_dimension_false(self):
        sandbox = Sandbox("sandbox", True)
        sandbox.include_in_sandbox_dimension = False

        self.assertEqual(
            '{"Name": "sandbox", "IncludeInSandboxDimension": false}',
            sandbox.body)
