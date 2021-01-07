# -*- coding: utf-8 -*-

from TM1py.Objects.GitCommit import GitCommit
from TM1py.Objects.GitRemote import GitRemote


class Git():
    """ Abstraction of Git object
    """
    def __init__(self, url: str, deployment: str, force: bool, deployed_commit: GitCommit, remote: GitRemote, config: dict = None):
        """ Initialize GIT object
        :param url: file or http(s) path to GIT repository
        :param deployment: name of selected deployment group
        :param force: whether or not Git context was forced
        :param deployed_commit: GitCommit object of the currently deployed commit
        :param remote: GitRemote object of the current remote
        :param config: Dictionary containing git configuration parameters

        """
        self._url = url
        self._deployment = deployment
        self._force = force
        self._deployed_commit = deployed_commit
        self._remote = remote
        self._config = config

    @property
    def url(self) -> str:
        return self._url

    @property
    def force(self) -> bool:
        return self._force

    @property
    def config(self) -> dict:
        return self._config

    @property
    def deployment(self) -> str:
        return self._deployment

    @property
    def deployed_commit(self) -> GitCommit:
        return self._deployed_commit

    @property
    def remote(self) -> GitRemote:
        return self._remote
