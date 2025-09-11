# -*- coding: utf-8 -*-
from abc import abstractmethod

from TM1py.Objects.TM1Object import TM1Object


class View(TM1Object):
    """Abstraction of TM1 View
    serves as a parentclass for TM1py.Objects.MDXView and TM1py.Objects.NativeView

    """

    def __init__(self, cube: str, name: str):
        self._cube = cube
        self._name = name

    @abstractmethod
    def body(self) -> str:
        pass

    @property
    def cube(self) -> str:
        return self._cube

    @property
    def name(self) -> str:
        return self._name

    @cube.setter
    def cube(self, value: str):
        self._cube = value

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def mdx(self):
        raise NotImplementedError
