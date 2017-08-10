# -*- coding: utf-8 -*-

import collections
import json

from TM1py.Objects.View import View


class MDXView(View):
    """ Abstraction on TM1 MDX view

        IMPORTANT. MDXViews can't be seen through the old TM1 clients (Archict, Perspectives). They do exist though!
    """
    def __init__(self, cube_name, view_name, MDX):
        View.__init__(self, cube_name, view_name)
        self._MDX = MDX

    @property
    def MDX(self):
        return self._MDX

    @MDX.setter
    def MDX(self, value):
        self._MDX = value

    @property
    def body(self):
        return self.construct_body()

    @classmethod
    def from_json(cls, view_as_json, cube_name=None):
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict, cube_name=None):
        return cls(cube_name=view_as_dict['Cube']['Name'] if not cube_name else cube_name,
                   view_name=view_as_dict['Name'],
                   MDX=view_as_dict['MDX'])

    def construct_body(self):
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._MDX
        return json.dumps(mdx_view_as_dict, ensure_ascii=False)
