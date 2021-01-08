# -*- coding: utf-8 -*-
import json
from typing import List

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService, Response
from TM1py.Objects.GitRemote import GitRemote
from TM1py.Objects.Git import Git
from TM1py.Objects.GitCommit import GitCommit
from TM1py.Objects.GitPlan import GitPushPlan, GitPullPlan, GitPlan
from TM1py.Utils.Utils import format_url


class GitService(ObjectService):
    """ Service to interact with GIT
    """
    def __init__(self, rest: RestService):
        super().__init__(rest)

    def from_json(self, json_response: str) -> Git:
        deployed_commit = GitCommit(
            commit_id=json_response["DeployedCommit"].get("ID"),
            summary=json_response["DeployedCommit"].get("Summary"),
            author=json_response["DeployedCommit"].get("Author")
            )

        remote = GitRemote(
            connected=json_response["Remote"].get("Connected"),
            branches=json_response["Remote"].get("Branches"),
            tags=json_response["Remote"].get("Tags"),
            )

        git = Git(
            url=json_response["URL"],
            deployment=json_response["Deployment"],
            force=json_response["Deployment"],
            deployed_commit=deployed_commit,
            remote=remote)

        return git

    def git_init(self, git_url: str, deployment: str, username: str = None, password: str = None, public_key: str = None,
                private_key: str = None, passphrase: str = None, force: bool = None, config: dict = None,  **kwargs) -> Git:
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
        body = {}
        body['URL'] = git_url
        body['Deployment'] = deployment

        if username is not None:
            body['Username'] = username
        if password is not None:
            body['Password'] = password
        if public_key is not None:
            body['PublicKey'] = public_key
        if private_key is not None:
            body['PrivateKey'] = private_key
        if passphrase is not None:
            body['Passphrase'] = passphrase
        if force is not None:
            body['Force'] = force
        if config is not None:
            body['Config'] = config
        
        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        return self.from_json(response.json())

    def git_uninit(self, force=False):
        """ Unitialize GIT service
        :param Force: clean up gitcontext when True
        """
        url = "/api/v1/GitUninit"
        body = json.dumps(force)
        return self._rest.POST(url=url, data=body)

    def git_status(self, username: str = None, password: str = None, public_key: str = None, private_key: str = None,
                    passphrase: str = None, **kwargs) -> Git:
        """ Get GIT status, returns Git object
        :param Username: GIT username
        :param Password: GIT password
        :param PublicKey: SSH public key, available from PAA V2.0.9.4
        :param PrivateKey: SSH private key, available from PAA V2.0.9.4
        :param Passphrase: Passphrase for decrypting private key, if set
        """
        url = "/api/v1/GitStatus"
        body = {}

        if username is not None:
            body['Username'] = username
        if password is not None:
            body['Password'] = password
        if public_key is not None:
            body['PublicKey'] = public_key
        if private_key is not None:
            body['PrivateKey'] = private_key
        if passphrase is not None:
            body['Passphrase'] = passphrase
        
        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        return self.from_json(response.json())

    def git_push(self, message: str, author: str, email: str, branch: str = None, new_branch: str = None, force: bool = None, username: str = None,
                    password: str = None, public_key: str = None, private_key: str = None, passphrase: str = None, execute: bool = None,
                    **kwargs) -> Response:
        """ Creates a gitpush plan, returns response
        :param message: Commit message
        :param author: Name of commit author
        :param email: Email of commit author
        :param branch: The branch which last commit will be used as parent commit for new branch. Must be empty if GIT repo is empty
        :param new_branch: If specified, creates a new branch and pushes the commit onto it. If not specified, pushes to the branch specified in "Branch"
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

        if message is not None:
            body['Message'] = message
        if author is not None:
            body['Author'] = author
        if email is not None:
            body['Email'] = email
        if branch is not None:
            body['Branch'] = branch
        if new_branch is not None:
            body['NewBranch'] = new_branch
        if force is not None:
            body['Force'] = force
        if username is not None:
            body['Username'] = username
        if password is not None:
            body['Password'] = password
        if public_key is not None:
            body['PublicKey'] = public_key
        if private_key is not None:
            body['PrivateKey'] = private_key
        if passphrase is not None:
            body['Passphrase'] = passphrase

        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        if execute:
            plan_id = json.loads(response.content).get('ID')
            self.git_execute_plan(plan_id=plan_id)

        return response

    def git_pull(self, branch: str, force: bool = None, execute: bool = None, username: str = None, password: str = None, 
                public_key: str = None, private_key: str = None, passphrase: str = None, **kwargs) -> Response:
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

        if branch is not None:
            body['Branch'] = branch
        if force is not None:
            body['Force'] = force
        if username is not None:
            body['Username'] = username
        if password is not None:
            body['Password'] = password
        if public_key is not None:
            body['PublicKey'] = public_key
        if private_key is not None:
            body['PrivateKey'] = private_key
        if passphrase is not None:
            body['Passphrase'] = passphrase

        body_json = json.dumps(body)
        response = self._rest.POST(url=url, data=body_json, **kwargs)

        if execute:
            plan_id = json.loads(response.content).get('ID')
            self.git_execute_plan(plan_id=plan_id)

        return response

    def git_execute_plan(self, plan_id) -> Response:
        """ Executes a plan based on the planid
        :param planid: GitPlan id
        """
        url = format_url("/api/v1/GitPlans('{}')/tm1.Execute",plan_id)
        return self._rest.POST(url=url)

    def git_get_plans(self, **kwargs) -> List[GitPlan]:
        """ Gets a list of currently available GIT plans
        """
        url = "/api/v1/GitPlans"
        plans = []
        response_dict = json.loads(self._rest.GET(url=url, body=kwargs).content)
        # Every individual plan is wrapped in a "value" parent, iterate through those to get the actual plans
        for plan in response_dict.get('value'):
            plan_id = plan.get('ID')
            # Check if plan has an ID, sometimes there's a null in the mix that we don't want
            if plan_id is None:
                continue
            plan_branch = plan.get('Branch')
            plan_force = plan.get('Force')

            # A git plan can either be a PushPlan or a PullPlan, these have slightly different variables, so we need to handle those differently
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
                current_plan = GitPullPlan(plan_id=plan_id, branch=plan_branch, force=plan_force, commit=plan_commit, operations=plan_operations)

            else:
                raise ValueError("Invalid plan detected")
            
            plans.append(current_plan)
            return plans
