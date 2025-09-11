import unittest

from TM1py.Objects.GitProject import TM1Project, TM1ProjectTask, TM1ProjectDeployment


class TestGitProject(unittest.TestCase):

    def test_add_task_process(self):
        project = TM1Project(name="TM1py Tests")

        project.add_task(
            TM1ProjectTask(
                "TaskA",
                process="bedrock.server.savedataall",
                parameters=[{"param_name": "sPar1", "param_val": "1"}],
                dependencies=["Tasks('TaskB')"],
            )
        )

        project.add_task(
            TM1ProjectTask("TaskB", chore="Chores('bedrock.server.savedataall')", dependencies=["Tasks('TaskA')"])
        )

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Tasks": {
                "TaskA": {
                    "Process": "Processes('bedrock.server.savedataall')",
                    "Parameters": [{"param_name": "sPar1", "param_val": "1"}],
                    "Dependencies": ["Tasks('TaskB')"],
                },
                "TaskB": {"Chore": "Chores('bedrock.server.savedataall')", "Dependencies": ["Tasks('TaskA')"]},
            },
        }

        self.assertEqual(expected_body, project.body_as_dict)

    def test_remove_task_process(self):
        project = TM1Project(name="TM1py Tests")

        project.add_task(TM1ProjectTask("TaskA", process="bedrock.server.savedataall"))
        project.add_task(TM1ProjectTask("TaskB", process="bedrock.server.wait"))
        project.remove_task(task_name="TaskB")

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Tasks": {"TaskA": {"Process": "Processes('bedrock.server.savedataall')"}},
        }

        self.assertEqual(expected_body, project.body_as_dict)

    def test_add_ignore(self):
        project = TM1Project(name="TM1py Tests")
        project.add_ignore(object_class="Dimensions", object_name="Dim*")

        expected_body = {"Version": 1.0, "Name": "TM1py Tests", "Ignore": ["Dimensions('Dim*')"]}
        self.assertEqual(expected_body, project.body_as_dict)

    def test_remove_ignore(self):
        project = TM1Project(name="TM1py Tests")
        project.add_ignore(object_class="Dimensions", object_name="Dim*")
        project.add_ignore(object_class="Cubes", object_name="Cubetoberemoved")
        project.remove_ignore(ignore_entry="Cubes('Cubetoberemoved')")

        expected_body = {"Version": 1.0, "Name": "TM1py Tests", "Ignore": ["Dimensions('Dim*')"]}
        self.assertEqual(expected_body, project.body_as_dict)

    def test_add_ignore_exception(self):
        project = TM1Project(name="TM1py Tests")
        project.add_ignore(object_class="Dimensions", object_name="Dim*")
        project.add_ignore_exceptions(object_class="Dimensions", object_names=["DimA", "DimB"])
        project.add_ignore_exceptions(object_class="Dimensions", object_names=["DimC", "DimD"])
        project.remove_ignore(ignore_entry="!Dimensions('DimA')")
        project.remove_ignore(ignore_entry="!Dimensions('DimB')")

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Ignore": ["Dimensions('Dim*')", "!Dimensions('DimC')", "!Dimensions('DimD')"],
        }
        self.assertEqual(expected_body, project.body_as_dict)

    def test_add_deployment(self):
        project = TM1Project(name="TM1py Tests")
        project.add_deployment(
            TM1ProjectDeployment(
                deployment_name="Dev",
                settings={"ServerName": "dev"},
                tasks={"TaskA": TM1ProjectTask(task_name="TaskA", process="bedrock.server.savedataall")},
                pre_push=["TaskA", "TaskB"],
            )
        )

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Deployment": {
                "Dev": {
                    "Settings": {"ServerName": "dev"},
                    "Tasks": {"TaskA": {"Process": "Processes('bedrock.server.savedataall')"}},
                    "PrePush": ["TaskA", "TaskB"],
                }
            },
        }

        self.assertEqual(expected_body, project.body_as_dict)

    def test_remove_deployment(self):
        project = TM1Project(name="TM1py Tests")
        project.add_deployment(
            TM1ProjectDeployment(
                deployment_name="Dev",
                settings={"ServerName": "dev"},
                tasks={"TaskA": TM1ProjectTask(task_name="TaskA", process="bedrock.server.savedataall")},
                pre_push=["TaskA", "TaskB"],
            )
        )
        project.add_deployment(
            TM1ProjectDeployment(
                deployment_name="Prod",
                settings={"ServerName": "prod"},
                tasks={"TaskA": TM1ProjectTask(task_name="TaskA", process="bedrock.server.savedataall")},
                pre_push=["TaskA", "TaskB"],
            )
        )
        project.remove_deployment("Dev")

        expected_body = {
            "Version": 1.0,
            "Name": "TM1py Tests",
            "Deployment": {
                "Prod": {
                    "Settings": {"ServerName": "prod"},
                    "Tasks": {"TaskA": {"Process": "Processes('bedrock.server.savedataall')"}},
                    "PrePush": ["TaskA", "TaskB"],
                }
            },
        }

        self.assertEqual(expected_body, project.body_as_dict)


if __name__ == "__main__":
    unittest.main()
