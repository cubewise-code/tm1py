# -*- coding: utf-8 -*-


class GitCommit:
    """Abstraction of Git Commit"""

    def __init__(self, commit_id: str, summary: str, author: str):
        """Initialize GitCommit object
        :param commit_id: id of the commit
        :param summary: commit message
        :param author: the author of the commit
        """
        self._commit_id = commit_id
        self._summary = summary
        self._author = author

    @property
    def commit_id(self) -> str:
        return self._commit_id

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def author(self) -> str:
        return self._author
