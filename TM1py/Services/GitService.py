# -*- coding: utf-8 -*-
import json
from typing import List

from TM1py.Objects.Git import Git
from TM1py.Objects.GitCommit import GitCommit
from TM1py.Objects.GitPlan import GitPushPlan, GitPullPlan, GitPlan
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService, Response
from TM1py.Utils.Utils import format_url
from TM1py.Objects.GitProject import TM1Project


class GitService(ObjectService):
    """ Service to interact with GIT
    """
    COMMON_PARAMETERS = {'username': 'Username', 'password': 'Password', 'message': 'Message', 'author': 'Author',
                         'email': 'Email', 'branch': 'Branch', 'new_branch': 'NewBranch', 'force': 'Force',
                         'public_key': 'PublicKey', 'private_key': 'PrivateKey', 'passphrase': 'Passphrase',
                         'config': 'Config'}

    def __init__(self, rest: RestService):
        super().__init__(rest)
        
    def tm1project_get(self) -> TM1Project:
        """_summary_
        """
        url = '/api/v1/!tm1project'
        tm1project = self._rest.GET(url)
        
        return TM1Project.from_dict(tm1project.json())
    
    def tm1project_delete(self):
        url = '/api/v1/!tm1project'
        empty_dict = {}
        body_json = json.dumps(empty_dict)
        
        response = self._rest.PUT(url, data=body_json)
        return TM1Project.from_dict(response.json())
        
    def tm1project_put(self, tm1_project: TM1Project) -> Response:
        url = '/api/v1/!tm1project'
        body_json = tm1_project.body
        
        response = self._rest.PUT(url=url,data=body_json)
        return TM1Project.from_dict(response.json())

    def git_init(self, git_url: str, deployment: str, username: str = None, password: str = None,
                 public_key: str = None, private_key: str = None, passphrase: str = None, force: bool = None,
                 config: dict = None, **kwargs) -> Git:
        """ Initialize GIT service, returns Git object
        :param git_url: file or http(s) path to GIT repository
        :param deployment: name of selected deployment group
        :param username: GIT username
        :param password: GIT password
        :param public_key: SSH public key, available from PAA V2.0.9.4
        :param private_key: SSH private key, available from PAA V2.0.9.4
        :param passphrase: Passphrase for decrypting private key, if set
        :param force: reset git context on True
        :param config: Dictionary containing git configuration parameters
        """
        url = "/api/v1/GitInit"
        body = {'URL': git_url, 'Deployment': deployment}

        for key, value in locals().items():
            if value is not None and key in self.COMMON_PARAMETERS.keys():
                body[self.COMMON_PARAMETERS.get(key)] = value

        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        return Git.from_dict(response.json())

    def git_uninit(self, force: bool = False, **kwargs):
        """ Unitialize GIT service

        :param force: clean up git context when True
        """
        url = "/api/v1/GitUninit"
        body = json.dumps(force)
        return self._rest.POST(url=url, data=body, **kwargs)

    def git_status(self, username: str = None, password: str = None, public_key: str = None, private_key: str = None,
                   passphrase: str = None, **kwargs) -> Git:
        """ Get GIT status, returns Git object
        :param username: GIT username
        :param password: GIT password
        :param public_key: SSH public key, available from PAA V2.0.9.4
        :param private_key: SSH private key, available from PAA V2.0.9.4
        :param passphrase: Passphrase for decrypting private key, if set
        """
        url = "/api/v1/GitStatus"
        body = {}

        for key, value in locals().items():
            if value is not None and key in self.COMMON_PARAMETERS.keys():
                body[self.COMMON_PARAMETERS.get(key)] = value

        response = self._rest.POST(url=url, data=json.dumps(body), **kwargs)

        return Git.from_dict(response.json())

    def git_push(self, message: str, author: str, email: str, branch: str = None, new_branch: str = None,
                 force: bool = False, username: str = None, password: str = None, public_key: str = None,
                 private_key: str = None, passphrase: str = None, execute: bool = None, **kwargs) -> Response:
        """ Creates a gitpush plan, returns response
        :param message: Commit message
        :param author: Name of commit author
        :param email: Email of commit author
        :param branch: The branch which last commit will be used as parent commit for new branch.
        Must be empty if GIT repo is empty
        :param new_branch: If specified, creates a new branch and pushes the commit onto it. If not specified,
        pushes to the branch specified in "Branch"
        :param force: A flag passed in for evaluating preconditions
        :param username: GIT username
        :param password: GIT password
        :param public_key: SSH public key, available from PAA V2.0.9.4
        :param private_key: SSH private key, available from PAA V2.0.9.4
        :param passphrase: Passphrase for decrypting private key, if set
        :param execute: Executes the plan right away if True

        """
        url = "/api/v1/GitPush"
        body = {}

        for key, value in locals().items():
            if value is not None and key in self.COMMON_PARAMETERS.keys():
                body[self.COMMON_PARAMETERS.get(key)] = value

        response = self._rest.POST(url=url, data=json.dumps(body), **kwargs)

        if execute:
            plan_id = json.loads(response.content).get('ID')
            self.git_execute_plan(plan_id=plan_id)

        return response

    def git_pull(self, branch: str, force: bool = None, execute: bool = None, username: str = None,
                 password: str = None, public_key: str = None, private_key: str = None, passphrase: str = None,
                 **kwargs) -> Response:
        """ Creates a gitpull plan, returns response
        :param branch: The name of source branch
        :param force: A flag passed in for evaluating preconditions
        :param execute: Executes the plan right away if True
        :param username: GIT username
        :param password: GIT password
        :param public_key: SSH public key, available from PAA V2.0.9.4
        :param private_key: SSH private key, available from PAA V2.0.9.4
        :param passphrase: Passphrase for decrypting private key, if set
        """
        url = "/api/v1/GitPull"
        body = {}

        for key, value in locals().items():
            if value is not None and key in self.COMMON_PARAMETERS.keys():
                body[self.COMMON_PARAMETERS.get(key)] = value

        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        if execute:
            plan_id = json.loads(response.content).get('ID')
            self.git_execute_plan(plan_id=plan_id)

        return response

    def git_execute_plan(self, plan_id: str, **kwargs) -> Response:
        """ Executes a plan based on the planid
        :param plan_id: GitPlan id
        """
        url = format_url("/api/v1/GitPlans('{}')/tm1.Execute", plan_id)
        return self._rest.POST(url=url, **kwargs)

    def git_get_plans(self, **kwargs) -> List[GitPlan]:
        """ Gets a list of currently available GIT plans
        """
        url = "/api/v1/GitPlans"
        plans = []

        response = self._rest.GET(url=url, **kwargs)

        # Every individual plan is wrapped in a "value" parent, iterate through those to get the actual plans
        for plan in response.json().get('value'):
            plan_id = plan.get('ID')
            # Check if plan has an ID, sometimes there's a null in the mix that we don't want
            if plan_id is None:
                continue
            plan_branch = plan.get('Branch')
            plan_force = plan.get('Force')

            # A git plan can either be a PushPlan or a PullPlan, these have slightly different variables,
            # so we need to handle those differently
            if plan.get('@odata.type') == '#ibm.tm1.api.v1.GitPushPlan':
                plan_new_branch = plan.get('NewBranch')
                plan_source_files = plan.get('SourceFiles')

                new_commit = GitCommit(
                    commit_id=plan.get('NewCommit').get('ID'),
                    summary=plan.get('NewCommit').get('Summary'),
                    author=plan.get('NewCommit').get('Author'))

                parent_commit = GitCommit(
                    commit_id=plan.get('ParentCommit').get('ID'),
                    summary=plan.get('ParentCommit').get('Summary'),
                    author=plan.get('ParentCommit').get('Author'))

                current_plan = GitPushPlan(
                    plan_id=plan_id, branch=plan_branch, force=plan_force,
                    new_branch=plan_new_branch, new_commit=new_commit,
                    parent_commit=parent_commit, source_files=plan_source_files)

            elif plan.get('@odata.type') == '#ibm.tm1.api.v1.GitPullPlan':

                plan_commit = GitCommit(
                    commit_id=plan.get('Commit').get('ID'),
                    summary=plan.get('Commit').get('Summary'),
                    author=plan.get('Commit').get('Author'))

                plan_operations = plan.get('Operations')
                current_plan = GitPullPlan(plan_id=plan_id, branch=plan_branch, force=plan_force, commit=plan_commit,
                                           operations=plan_operations)

            else:
                raise RuntimeError(f"Invalid plan detected: {plan.get('@odata.type')}")

            plans.append(current_plan)

        return plans
