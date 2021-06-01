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
        View.__init__(self, cube_name, view_name)
        self._mdx = MDX

    @property
    def mdx(self):
        return self._mdx

    @mdx.setter
    def mdx(self, value: str):
        self._mdx = value

    @property
    def MDX(self) -> str:
        return self._mdx

    @MDX.setter
    def MDX(self, value: str):
        self._mdx = value

    @property
    def body(self) -> str:
        return self.construct_body()

    @classmethod
    def from_json(cls, view_as_json: str, cube_name: Optional[str] = None) -> 'MDXView':
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict: Dict, cube_name: str = None) -> 'MDXView':
        return cls(cube_name=view_as_dict['Cube']['Name'] if not cube_name else cube_name,
                   view_name=view_as_dict['Name'],
                   MDX=view_as_dict['MDX'])

    def construct_body(self) -> str:
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._mdx
        return json.dumps(mdx_view_as_dict, ensure_ascii=False)
