    # -*- coding: utf-8 -*-

import json
from typing import Optional, Dict, List

from TM1py.Objects.TM1Object import TM1Object


def clean_null_terms(d: Dict):
    clean = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = clean_null_terms(v)
            if len(nested.keys()) > 0:
                clean[k] = nested
        elif isinstance(v, list) and not d[k]:
            continue
        elif v is not None:
            clean[k] = v
    return clean


class TM1ProjectTask:

    def __init__(self, task_name: str, chore: str = None, process: str = None, parameters: List[Dict[str, str]] = None,
                 dependencies: List[str] = None, precondition: str = None):
        """
        Defines an action that executes a Process or a Chore with certain parameters.

        A Task MUST either have a Process or a Chore property.
        The property specifies the reference of the Process or Chore to be executed.
        The Process or Chore MUST be visible.

        A Task MAY have a Parameters property.
        The property specifies the parameters to be passed to the Process.
        This property MUST NOT be specified if the task is to execute a Chore.

        A Task MAY have a Dependencies property.
        The property specifies an array of URIs of tasks or objects,
        which will be executed or loaded, respectively, before executing the current task.
        E.g.: ["Cubes('Cube_A')", "Dimensions('Dimension_C')"]

        A Task MAY have a Precondition property.
        The server only executes a Task when either the precondition is not specified, or it is evaluated to TRUE.

        The server only executes a Task one time during a deployment.
        """

        if not any([chore, process]):
            raise ValueError("TM1ProjectTask must either have a 'Process' or a 'Chore' property")

        if all([chore, process]):
            raise ValueError("TM1ProjectTask must not have a 'Chore' and 'Process' property")

        if all([chore, parameters]):
            raise ValueError("TM1ProjectTask must not have a 'Chore' and 'Parameters' property")

        self.task_name = task_name
        self.chore = chore
        self.process = process
        self.parameters = parameters
        self.dependencies = dependencies
        self.precondition = precondition

    def construct_body(self) -> Dict:
        body = dict()
        
        if self.chore:
            if not self.chore.startswith("Chores('"):
                body = {
                    "Chore": f"Chores('{self.chore}')"
                }
            else:
                body["Chore"] = self.chore
        else:
            if not self.process.startswith("Processes('"):
                body = {
                    "Process": f"Processes('{self.process}')",
                }
            else:
                body["Process"] = self.process
            body.update({"Parameters": self.parameters})
        
        if self.dependencies:
            body["Dependencies"] = self.dependencies

        return body

    @classmethod
    def from_dict(cls, task_name: str, task: Dict):
        return cls(
            task_name=task_name,
            chore=task.get("Chore"),
            process=task.get("Process"),
            parameters=task.get("Parameters"),
            dependencies=task.get("Dependencies"),
            precondition=task.get("Precondition"),
        )


class TM1Project(TM1Object):
    """ Abstraction of Git tm1project
    """

    def __init__(
            self,
            version: int = 1.0,
            name: Optional[str] = '',
            settings: Optional[Dict] = None,
            tasks: Optional[Dict[str, TM1ProjectTask]] = None,
            objects: Optional[Dict] = None,
            ignore: Optional[List] = None,
            files: Optional[List] = None,
            deployment: Optional[Dict] = None,
            pre_push: Optional[List] = None,
            post_push: Optional[List] = None,
            pre_pull: Optional[List] = None,
            post_pull: Optional[List] = None):
        """

        Args:
            version (int): _description_
            settings (dict, optional): _description_. Defaults to None.
            tasks (dict, optional): _description_. Defaults to None.
            objects (dict, optional): _description_. Defaults to None.
            ignore (list, optional): _description_. Defaults to None.
            files (list, optional): _description_. Defaults to None.
            deployment (dict, optional): _description_. Defaults to None.
            pre_push (list, optional): _description_. Defaults to None.
            post_push (list, optional): _description_. Defaults to None.
            pre_pull (list, optional): _description_. Defaults to None.
            post_pull (list, optional): _description_. Defaults to None.
        """
        self._version = version
        self._name = name
        self._settings = settings
        self._tasks = tasks
        self._objects = objects
        self._ignore = ignore
        self._files = files
        self._deployment = deployment
        self._pre_push = pre_push
        self._post_push = post_push
        self._pre_pull = pre_pull
        self._post_pull = post_pull

    def add_task(self, project_task: TM1ProjectTask):
        if self._tasks is None:
            self._tasks = dict()

        if project_task.task_name in self._tasks:
            raise ValueError(f"Task with name '{project_task.task_name}' already exists in TM1 project. "
                             f"Task name must be unique")

        self._tasks[project_task.task_name] = project_task

    def remove_task(self, task_name: str):
        if task_name in self._tasks:
            self._tasks.pop(task_name, None)

    def include_all_attribute_dimensions(self, tm1):
        """
        Add an ignore-exception for each attribute dimension

        """
        attribute_dimensions = [
            dimension
            for dimension
            in tm1.dimensions.get_all_names()
            if dimension.lower().startswith("}elementattributes_")]

        self.add_ignore_exceptions("Dimensions", attribute_dimensions)

    def add_ignore_exceptions(self, object_class: str, object_names: List[str]):
        """
        Specify exceptions to ignore policy.
        Wildcards (`*`) can not be used in the `object_name`

        Args:
            object_class: class of the object e.g., "Dimensions"
            object_names: names of the objects e.g., ["Product", "Customer", "Region"]

        Example of the ignore property in the tm1project:
            Exclude all Dimensions that start with 'Dim', except for dimension 'DimB', 'DimA'

            "Ignore":
            [
              "Dimensions('Dim*')",
              "!Dimensions('DimA')",
              "!Dimensions('DimB')"
            ]
        """

        for object_name in object_names:
            if "*" in object_name:
                raise ValueError("'*' character must not be used in object_name")

            ignore_entry = "!" + object_class
            if object_name:
                ignore_entry += f"('{object_name}')"

            if self.ignore is None:
                self.ignore = []

            if ignore_entry not in self.ignore:
                self.ignore.append(ignore_entry)

    def add_ignore(self, object_class: str, object_name: str):
        """
        Ignore is an optional property in the tm1project
        It specifies the objects to be excluded from the source, if the object is newly created.

        Args:
            object_class: class of the object e.g., "Dimensions"
            object_name: name of the object e.g., "Product"

        For the `object_type` pass value like `Dimensions` or `Cubes/Views`

        Wildcards (`*`) can be used in the `object_name`, if the object is not a control object.

        Example of the `ignore` property in the tm1project:
            Exclude all the new Cubes and Views in the source, except Cube_A;
            include control Process }Drill_Drill_A;
            and exclude all the new Dimensions which has a name starting with 'Dim'

            "Ignore":
            [
              "Cubes/Views",
              "!Cubes('Cube_A')",
              "!Processes('}Drill_Drill_A')",
              "Dimensions('Dim*')"
            ]
        """

        if object_name.startswith("}") and "*" in object_name:
            raise ValueError("'*' character must not be used in object_name for control objects")

        if self.ignore is None:
            self.ignore = []

        ignore_entry = object_class
        if object_name:
            ignore_entry += f"('{object_name}')"

        if ignore_entry not in self.ignore:
            self.ignore.append(ignore_entry)

    def remove_ignore(self, ignore_entry: str):
        if ignore_entry in self.ignore:
            self.ignore.remove(ignore_entry)

    def add_deployment(self, deployment: 'TM1ProjectDeployment'):
        """
        "Deployment is an OPTIONAL property. Each of its property defines a named deployment and its specific properties.
        All the tm1project properties can be redefined for a deployment, except Version.
        Those properties override the tm1project properties for the specific deployment.

        Current deployment is set by action GitInit."

        """
        if self._deployment is None:
            self._deployment = dict()

        if deployment._deployment_name in self._deployment:
            raise ValueError(f"Deployment with name '{deployment._deployment_name}' already exists in TM1 project. "
                             f"Deployment name must be unique")

        self._deployment[deployment._deployment_name] = deployment

    def remove_deployment(self, deployment_name: str):
        if deployment_name in self._deployment:
            self._deployment.pop(deployment_name, None)

    @classmethod
    def from_json(cls, tm1project_as_json: str) -> 'TM1Project':
        """
        :param tm1project_as_json: response of /!tm1project
        :return: an instance of this class
        """
        tm1project_as_dict = json.loads(tm1project_as_json)
        return cls.from_dict(tm1project_as_dict=tm1project_as_dict)

    @classmethod
    def from_dict(cls, tm1project_as_dict: Dict) -> 'TM1Project':
        """
        :param tm1project_as_dict: Dictionary, tm1project as dictionary
        :return: an instance of this class
        """
        return cls(
            version=tm1project_as_dict['Version'],
            name=tm1project_as_dict.get('Name'),
            settings=tm1project_as_dict.get('Settings'),
            tasks={
                task_name: TM1ProjectTask.from_dict(task_name, task)
                for task_name, task
                in tm1project_as_dict.get('Tasks').items()} if "Tasks" in tm1project_as_dict else {},
            objects=tm1project_as_dict.get('Objects'),
            ignore=tm1project_as_dict.get('Ignore'),
            files=tm1project_as_dict.get('Files'),
            deployment={
                deployment_name: TM1ProjectDeployment.from_dict(deployment_name, deployment)
                for deployment_name, deployment
                in tm1project_as_dict.get('Deployment').items()} if "Deployment" in tm1project_as_dict else {},
            pre_push=tm1project_as_dict.get('PrePush'),
            post_push=tm1project_as_dict.get('PostPush'),
            pre_pull=tm1project_as_dict.get('PrePull'),
            post_pull=tm1project_as_dict.get('PostPull'),
        )

    @classmethod
    def from_file(cls, filename: str) -> 'TM1Project':
        with open(filename, 'r') as file_object:
            json_file = json.load(file_object)

        return cls.from_dict(json_file)

    # construct self.body (json) from the class-attributes
    def _construct_body(self) -> Dict:
        body = {
            'Version': self._version,
            'Name': self._name,
            'Settings': self._settings,
            'Tasks': {name: task.construct_body() for name, task in self.tasks.items()} if self._tasks else None,
            'Objects': self._objects,
            'Ignore': self._ignore,
            'Files': self._files,
            'Deployment': {
                name: deployment.construct_body()
                for name, deployment
                in self._deployment.items()} if self._deployment else None,
            'PrePush': self._pre_push,
            'PostPush': self._post_push,
            'PrePull': self._pre_pull,
            'PostPull': self._post_pull}
        return clean_null_terms(body)

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    @property
    def body(self) -> str:
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    @property
    def version(self) -> int:
        return self._version

    @version.setter
    def version(self, value: int):
        self._version = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def settings(self) -> dict:
        return self._settings

    @settings.setter
    def settings(self, value: Dict):
        self._settings = value

    @property
    def tasks(self) -> Dict:
        return self._tasks

    @tasks.setter
    def tasks(self, value: List):
        self._tasks = value

    @property
    def objects(self) -> Dict:
        return self._objects

    @objects.setter
    def objects(self, value: Dict):
        self._objects = value

    @property
    def ignore(self) -> List:
        return self._ignore

    @ignore.setter
    def ignore(self, value: List):
        self._ignore = value

    @property
    def deployment(self) -> Dict:
        return self._deployment

    @deployment.setter
    def deployment(self, value: Dict):
        self._deployment = value

    @property
    def pre_push(self) -> list:
        return self._pre_push

    @pre_push.setter
    def pre_push(self, value: list):
        self._pre_push = value

    @property
    def post_push(self) -> list:
        return self._post_push

    @post_push.setter
    def post_push(self, value: list):
        self._post_push = value

    @property
    def pre_pull(self) -> list:
        return self._pre_pull

    @pre_pull.setter
    def pre_pull(self, value: list):
        self._pre_pull = value

    @property
    def post_pull(self) -> list:
        return self._post_pull

    @post_pull.setter
    def post_pull(self, value: list):
        self._post_pull = value


class TM1ProjectDeployment(TM1Project):
    def __init__(
            self,
            deployment_name: str,
            settings: Optional[Dict] = None,
            tasks: Optional[Dict[str, TM1ProjectTask]] = None,
            objects: Optional[Dict] = None,
            ignore: Optional[List] = None,
            files: Optional[List] = None,
            pre_push: Optional[List] = None,
            post_push: Optional[List] = None,
            pre_pull: Optional[List] = None,
            post_pull: Optional[List] = None):
        super().__init__(
            version=None,
            name=deployment_name,
            settings=settings,
            tasks=tasks,
            objects=objects,
            ignore=ignore,
            files=files,
            pre_push=pre_push,
            post_push=post_push,
            pre_pull=pre_pull,
            post_pull=post_pull)

        self._deployment_name = deployment_name

    @classmethod
    def from_dict(cls, deployment_name: str, deployment: Dict) -> 'TM1ProjectDeployment':
        """
        :param deployment_as_dict: Dictionary, deployment as dictionary
        :return: an instance of this class
        """
        return cls(
            deployment_name=deployment_name,
            settings=deployment.get('Settings'),
            tasks={
                task_name: TM1ProjectTask.from_dict(task_name, task)
                for task_name, task
                in deployment.get('Tasks').items()},
            objects=deployment.get('Objects'),
            ignore=deployment.get('Ignore'),
            files=deployment.get('Files'),
            pre_push=deployment.get('PrePush'),
            post_push=deployment.get('PostPush'),
            pre_pull=deployment.get('PrePull'),
            post_pull=deployment.get('PostPull')
        )

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    @property
    def body(self) -> str:
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    # construct self.body (json) from the class-attributes
    def construct_body(self) -> Dict:
        body_as_dict = {
            'Settings': self._settings,
            'Tasks': {name: task.construct_body() for name, task in self.tasks.items()} if self._tasks else None,
            'Objects': self._objects,
            'Ignore': self._ignore,
            'Files': self._files,
            'PrePush': self._pre_push,
            'PostPush': self._post_push,
            'PrePull': self._pre_pull,
            'PostPull': self._post_pull
        }
        return clean_null_terms(body_as_dict)
