# -*- coding: utf-8 -*-

import collections
import json
import re
from typing import Optional, Dict

from TM1py.Objects.View import View
from TM1py.Utils import case_and_space_insensitive_equals


class MDXView(View):
    """ Abstraction on TM1 MDX view

        IMPORTANT. MDXViews can't be seen through the old TM1 clients (Archict, Perspectives). They do exist though!
    """

    def __init__(self, cube_name: str, view_name: str, MDX: str, meta: dict = {}):
        View.__init__(self, cube_name, view_name)
        self._mdx = MDX
        self._aliases = meta.get('Aliases', {})

    @property
    def mdx(self):
        return self._mdx
    
    @property
    def aliases(self) -> dict[str, str]:
        """ Returns a dictionary with aliases for dimensions in the MDX view 
        self._aliases =  {
            '[Account].[Account]': 'Description',
            '[Cost Center].[Cost Center]': 'Full Name',
        }
        return: 
            {
                'Account': 'Description',
                'Cost Center': 'Full Name'
            }
        """
        dimension_hierarchy_pattern = re.compile(r'\[(?P<dimension>[^\]]+)\]\.\[(?P<hierarchy>[^\]]+)\]')
        alias_pool = {}
        for dimension_hierarchy_tuple, alias in self._aliases.items():
            pattern_matches = dimension_hierarchy_pattern.search(dimension_hierarchy_tuple)
            if not pattern_matches:
                continue 
            dimension = pattern_matches.group('dimension')
            hierarchy = pattern_matches.group('hierarchy')
            alias_pool[dimension] = alias
            
        return alias_pool

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

    def substitute_title(self, dimension: str, hierarchy: str, element: str):
        """ dimension and hierarchy name are space sensitive!

        :param dimension:
        :param hierarchy:
        :param element:
        :return:
        """
        pattern = re.compile(r"\[" + dimension + r"\].\[" + hierarchy + r"\].\[(.*?)\]", re.IGNORECASE)
        findings = re.findall(pattern, self._mdx)

        if findings:
            self._mdx = re.sub(
                pattern=pattern,
                repl=f"[{dimension}].[{hierarchy}].[{element}]",
                string=self._mdx)
            return

        if hierarchy is None or case_and_space_insensitive_equals(dimension, hierarchy):
            pattern = re.compile(r"\[" + dimension + r"\].\[(.*?)\]", re.IGNORECASE)
            findings = re.findall(pattern, self._mdx)
            if findings:
                self._mdx = re.sub(
                    pattern=pattern,
                    repl=f"[{dimension}].[{element}]",
                    string=self._mdx)
                return

        raise ValueError(f"No selection in title with dimension: '{dimension}' and hierarchy: '{hierarchy}'")

    @classmethod
    def from_json(cls, view_as_json: str, cube_name: Optional[str] = None) -> 'MDXView':
        view_as_dict = json.loads(view_as_json)
        return cls.from_dict(view_as_dict, cube_name)

    @classmethod
    def from_dict(cls, view_as_dict: Dict, cube_name: str = None) -> 'MDXView':
        return cls(cube_name=view_as_dict['Cube']['Name'] if not cube_name else cube_name,
                   view_name=view_as_dict['Name'],
                   MDX=view_as_dict['MDX'],
                   Meta=view_as_dict.get('Meta', {})
                   )

    def construct_body(self) -> str:
        mdx_view_as_dict = collections.OrderedDict()
        mdx_view_as_dict['@odata.type'] = 'ibm.tm1.api.v1.MDXView'
        mdx_view_as_dict['Name'] = self._name
        mdx_view_as_dict['MDX'] = self._mdx
        return json.dumps(mdx_view_as_dict, ensure_ascii=False)
