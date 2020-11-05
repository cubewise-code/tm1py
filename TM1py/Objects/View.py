# -*- coding: utf-8 -*-
from abc import abstractmethod

from TM1py.Objects.TM1Object import TM1Object


class View(TM1Object):
    """ Abstraction of TM1 View
        serves as a parentclass for TM1py.Objects.MDXView and TM1py.Objects.NativeView

    """

    def __init__(self, cube: str, name: str):
        """
        Initialize a cube.

        Args:
            self: (todo): write your description
            cube: (todo): write your description
            name: (str): write your description
        """
        self._cube = cube
        self._name = name

    @abstractmethod
    def body(self) -> str:
        """
        Return the body.

        Args:
            self: (todo): write your description
        """
        pass

    @property
    def cube(self) -> str:
        """
        Return the cube.

        Args:
            self: (todo): write your description
        """
        return self._cube

    @property
    def name(self) -> str:
        """
        Returns the name of this node.

        Args:
            self: (todo): write your description
        """
        return self._name

    @cube.setter
    def cube(self, value: str):
        """
        Set the cube.

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._cube = value

    @name.setter
    def name(self, value: str):
        """
        Set the name of the message

        Args:
            self: (todo): write your description
            value: (str): write your description
        """
        self._name = value
