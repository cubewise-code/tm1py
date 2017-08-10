# -*- coding: utf-8 -*-

class View:
    """ Abstraction of TM1 View
        serves as a parentclass for TM1py.Objects.MDXView and TM1py.Objects.NativeView

    """
    def __init__(self, cube, name):
        self._cube = cube
        self._name = name

    @property
    def cube(self):
        return self._cube

    @property
    def name(self):
        return self._name

    @cube.setter
    def cube(self, value):
        self._cube = value

    @name.setter
    def name(self, value):
        self._name = value
