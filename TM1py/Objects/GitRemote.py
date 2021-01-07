# -*- coding: utf-8 -*-
from typing import List

from TM1py.Objects.TM1Object import TM1Object


class GitRemote(TM1Object):
    """ Abstraction of GitRemote
    """

    def __init__(self, connected: bool, branches: List[str], tags: List[str]):
        """ Initialize GitRemote object
        :param connected: is Git connected to remote
        :param branches: list of remote branches
        :param tags: list of remote tags
        """
        self._connected = connected
        self._branches = branches
        self._tags = tags

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def branches(self) -> List[str]:
        return self._branches
    @property
    def tags(self) -> List[str]:
        return self._tags
