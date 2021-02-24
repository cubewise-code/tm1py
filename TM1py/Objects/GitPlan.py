# -*- coding: utf-8 -*-
from typing import List

from TM1py.Objects.GitCommit import GitCommit


class GitPlan:
    """ Base GitPlan abstraction
    """

    def __init__(self, plan_id: str, branch: str, force: bool):
        """ Initialize GitPlan object
        :param plan_id: id of the Plan
        :param branch: current branch
        :param force: force git context reset
        """
        self._plan_id = plan_id
        self._branch = branch
        self._force = force

    @property
    def plan_id(self) -> str:
        return self._plan_id

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def force(self) -> bool:
        return self._force


class GitPushPlan(GitPlan):
    """ GitPushPlan abstraction based on GitPlan
    """

    def __init__(self, plan_id: str, branch: str, force: bool, new_branch: str, new_commit: GitCommit,
                 parent_commit: GitCommit, source_files: List[str]):
        """ Initialize GitPushPlan object
        :param plan_id: id of the PushPlan
        :param branch: current branch to base the pushplan on
        :param force: force git context reset
        :param new_branch: the new branch that will be pushed to
        :param new_commit: GitCommit of the new commit
        :param parent_commit: The current commit in the branch
        :param source_files: list of included files in the push
        """
        self._new_branch = new_branch
        self._new_commit = new_commit
        self._parent_commit = parent_commit
        self._source_files = source_files

        super().__init__(plan_id=plan_id, branch=branch, force=force)

    @property
    def new_branch(self) -> str:
        return self._new_branch

    @property
    def new_commit(self) -> GitCommit:
        return self._new_commit

    @property
    def parent_commit(self) -> GitCommit:
        return self._parent_commit

    @property
    def source_files(self) -> List[str]:
        return self._source_files


class GitPullPlan(GitPlan):
    """ GitPushPlan abstraction based on GitPlan
    """

    def __init__(self, plan_id: str, branch: str, force: bool, commit: GitCommit, operations: List[str]):
        """ Initialize GitPushPlan object
        :param plan_id: id of the PullPlan
        :param branch: current branch to base the pullplan on
        :param force: force git context reset
        :param commit: GitCommit of the commit to pull
        :param operations: list of changes made upon pulling
        """
        self._commit = commit
        self._operations = operations

        super().__init__(plan_id=plan_id, branch=branch, force=force)

    @property
    def commit(self) -> GitCommit:
        return self._commit

    @property
    def operations(self) -> List[str]:
        return self._operations
