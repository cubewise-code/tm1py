# -*- coding: utf-8 -*-

import collections
import json
from typing import Optional, Dict

from TM1py.Objects.View import View


class MDXView(View):
    """ Abstraction on TM1 MDX view

        IMPORTANT. MDXViews can't be seen through the old TM1 clients (Archict, Perspectives). They do exist though!
    """

    def __init__(self, cube_name: str, view_name: str, MDX: str):
        """
        Creates a new cube.

        Args:
            self: (todo): write your description
            cube_name: (str): write your description
            view_name: (str): write your description
            MDX: (float): write your description
        """
        View.__init__(self, cube_name, view_name)
        self._MDX = MDX

    @property
    def MDX(self) -> str:
        """
        Str : class : ~.

        Args:
            self: (todo): write your description
        """
        return self._MDX

    @MDX.setter
    def MDX(self, value: str):
        """
        Gets / sets the x value

        Args:
            self: (todo): write your description
            value: (todo): write your description
        """
        self._MDX = value

    @property
    def body(self) -> str:
        """
        Return the body.

        Args:
            self: (todo): write your description
        """
        return self.construct_body()

    @classmethod
    def from_json(cls, view_as_json: str, cube_name: Optional[str] = None) -> 'MDXView':
        """
        Create a : class from a cube.

        Args:
            cls: (todo): write your description
            view_as_json: (todo): write your description
            cube_name: (str): write your description
        """
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict: Dict, cube_name: str = None) -> 'MDXView':
        """
        Creates a cube from a cube.

        Args:
            cls: (todo): write your description
            view_as_dict: (dict): write your description
            cube_name: (str): write your description
        """
        return cls(cube_name=view_as_dict['Cube']['Name'] if not cube_name else cube_name,
                   view_name=view_as_dict['Name'],
                   MDX=view_as_dict['MDX'])

    def construct_body(self) -> str:
        """
        Constructs the body as a dict.

        Args:
            self: (todo): write your description
        """
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._MDX
        return json.dumps(mdx_view_as_dict, ensure_ascii=False)
