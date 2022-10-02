import unittest

from TM1py.Objects.GitProject import TM1Project, TM1ProjectTask


class TestGitProject(unittest.TestCase):

    def test_add_task_process(self):
        project = TM1Project(name="TM1py Tests")

        project.add_task(TM1ProjectTask("TaskA", process="bedrock.server.savedataall"))

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Tasks": [{"TaskA": {"Process": "bedrock.server.savedataall", "Parameters": None}}]}

        self.assertEqual(expected_body, project.body_as_dict)

    def test_add_ignore(self):
        project = TM1Project(name="TM1py Tests")
        project.add_ignore(object_class="Dimensions", object_name="Dim*")

        expected_body = {"Version": 1.0, "Name": "TM1py Tests", "Ignore": ["Dimensions('Dim*')"]}
        self.assertEqual(
            expected_body,
            project.body_as_dict)

    def test_add_ignore_exception(self):
        project = TM1Project(name="TM1py Tests")
        project.add_ignore(object_class="Dimensions", object_name="Dim*")
        project.add_ignore_exceptions(object_class="Dimensions", object_names=["DimA", "DimB"])

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Ignore": [
                "Dimensions('Dim*')",
                "!Dimensions('DimA')",
                "!Dimensions('DimB')"]
        }
        self.assertEqual(
            expected_body,
            project.body_as_dict)
