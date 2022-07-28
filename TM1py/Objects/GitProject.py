# -*- coding: utf-8 -*-

import json
from typing import Optional, Iterable, Dict, List, Union
from TM1py.Objects.TM1Object import TM1Object


def cleanNullTerms(d: dict):
    clean = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = cleanNullTerms(v)
            if len(nested.keys()) > 0:
                clean[k] = nested
        elif v is not None:
            clean[k] = v
    return clean


class TM1Project(TM1Object):
    """ Abstraction of Git tm1project
    """

    def __init__(self,
                 version: int = 1.0,
                 name: Optional[str] = '',
                 settings: Optional[dict] = None,
                 tasks: Optional[dict] = None,
                 objects: Optional[dict] = None,
                 ignore: Optional[list] = None,
                 files: Optional[list] = None,
                 deployment: Optional[dict] = None,
                 prepush: Optional[list] = None,
                 postpush: Optional[list] = None,
                 prepull: Optional[list] = None,
                 postpull: Optional[list] = None,
                 dependencies: Optional[list] = None,
                 preconditions: Optional[str] = ''):
        """_summary_

        Args:
            version (int): _description_
            settings (dict, optional): _description_. Defaults to None.
            tasks (dict, optional): _description_. Defaults to None.
            objects (dict, optional): _description_. Defaults to None.
            ignore (list, optional): _description_. Defaults to None.
            files (list, optional): _description_. Defaults to None.
            deployment (dict, optional): _description_. Defaults to None.
            prepush (list, optional): _description_. Defaults to None.
            postpush (list, optional): _description_. Defaults to None.
            prepull (list, optional): _description_. Defaults to None.
            postpull (list, optional): _description_. Defaults to None.
            dependencies (list, optional): _description_. Defaults to None.
        """
        self._version = version
        self._name = name
        self._settings = settings
        self._tasks = tasks
        self._objects = objects
        self._ignore = ignore
        self._files = files
        self._deployment = deployment
        self._prepush = prepush
        self._postpush = postpush
        self._prepull = prepull
        self._postpull = postpull
        self._dependencies = dependencies
        self._preconditions = preconditions

    @classmethod
    def from_json(cls, tm1project_as_json: str) -> 'TM1Project':
        """
        :param tm1project_as_json: response of /api/v1/!tm1project
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
        return cls(version=tm1project_as_dict['Version'],
                   name=tm1project_as_dict.get('Name'),
                   settings=tm1project_as_dict.get('Settings'),
                   tasks=tm1project_as_dict.get('Tasks'),
                   objects=tm1project_as_dict.get('Objects'),
                   ignore=tm1project_as_dict.get('Ignore'),
                   files=tm1project_as_dict.get('Files'),
                   deployment=tm1project_as_dict.get('Deployment'),
                   prepush=tm1project_as_dict.get('PrePush'),
                   postpush=tm1project_as_dict.get('PostPush'),
                   prepull=tm1project_as_dict.get('PrePull'),
                   postpull=tm1project_as_dict.get('PostPull'),
                   preconditions=tm1project_as_dict.get('Preconditions'),
                   dependencies=tm1project_as_dict.get('Dependencies')
                   )
    @classmethod
    def to_dict(cls, tm1_project) -> 'Dict':
        tm1_project_as_dict = tm1_project.__dict__
        return tm1_project_as_dict
    
    @classmethod
    def from_file(cls, filename:str) -> 'TM1Project':
        with open(filename, 'r') as file_object:
            json_file = json.load(file_object)
        return cls.from_dict(json_file)
     
    @property
    def body(self) -> str:
        return self._construct_body()

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
    def settings(self, value: dict):
        self._settings = value

    @property
    def tasks(self) -> dict:
        return self._tasks

    @tasks.setter
    def tasks(self, value: dict):
        self._tasks = value

    @property
    def objects(self) -> dict:
        return self._objects

    @objects.setter
    def objects(self, value: dict):
        self._objects = value

    @property
    def ignore(self) -> list:
        return self._ignore

    @ignore.setter
    def ignore(self, value: list):
        self._ignore = value

    @property
    def deployment(self) -> dict:
        return self._deployment

    @deployment.setter
    def deployment(self, value: dict):
        self._deployment = value

    @property
    def prepush(self) -> list:
        return self._prepush

    @prepush.setter
    def prepush(self, value: list):
        self._prepush = value

    @property
    def postpush(self) -> list:
        return self._postpush

    @postpush.setter
    def postpush(self, value: list):
        self._postpush = value

    @property
    def prepull(self) -> list:
        return self._prepull

    @prepull.setter
    def prepull(self, value: list):
        self._prepull = value

    @property
    def postpull(self) -> list:
        return self._postpull

    @postpull.setter
    def postpull(self, value: list):
        self._postpull = value

    @property
    def dependencies(self) -> list:
        return self._dependencies

    @dependencies.setter
    def dependencies(self, value: list):
        self._dependencies = value

    @property
    def preconditions(self) -> str:
        return self._preconditions

    @preconditions.setter
    def preconditions(self, value: str):
        self._preconditions = value

# construct self.body (json) from the class-attributes
    def _construct_body(self) -> str:
        # general parameters
        body_as_dict_complete = {
            'Version': self._version,
            'Name': self._name,
            'Settings': self._settings,
            'Tasks': self._tasks,
            'Objects': self._objects,
            'Ignore': self._ignore,
            'Files': self._files,
            'Deployment': self._deployment,
            'PrePush': self._prepush,
            'PostPush': self._postpush,
            'PrePull': self._prepull,
            'PostPull': self._postpull,
            'Dependencies': self._dependencies}

        body_as_dict = cleanNullTerms(body_as_dict_complete)
        return json.dumps(body_as_dict, ensure_ascii=False)
    