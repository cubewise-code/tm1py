# -*- coding: utf-8 -*-
import json
import re
from typing import Optional, Iterable, Dict, List, Union

from TM1py.Objects.TM1Object import TM1Object


class ProcessDebugBreakpoint(TM1Object):
    """ Abstraction of a TM1 Process Debug Breakpoing.

    """


    def __init__(self,
               breakpoint_type: str = '',
               breakpoint_id: int = 1,
               enabled: bool = True,
               hitmode: str = '',
               hitcount: int = 0,
               expression: str = '',
               variable_name: str = '',
               process_name: str = '',
               procedure: str = '',
               line_number: int = 0,
               object_name: str = '',
               object_type: str = '',
               lock_mode: str = ''
    ):

        self._type = breakpoint_type
        self._id = breakpoint_id
        self._enabled = enabled
        self._hitmode = hitmode
        self._hitcount = hitcount
        self._expression = expression
        self._variable_name = variable_name
        self._process_name = process_name
        self._procedure = procedure
        self._line_number = line_number
        self._object_name = object_name
        self._object_type = object_type
        self._lock_mode = lock_mode


    @classmethod
    def from_dict(cls, breakpoint_as_dict, **kwargs) -> 'ProcessDebugBreakpoint':
        """
        :param breakpoing
        :return: an instance of this class
        """
        breakpoint_type = breakpoint_as_dict['@odata.type'][16:]
        return cls(
            breakpoint_type=breakpoint_type,
            breakpoint_id=breakpoint_as_dict['ID'],
            enabled=breakpoint_as_dict['Enabled'],
            hitmode=breakpoint_as_dict['HitMode'],
            hitcount=breakpoint_as_dict['HitCount'],
            expression=breakpoint_as_dict['Expression'],
            variable_name=breakpoint_as_dict['VariableName'] if breakpoint_type == "ProcessDebugContextDataBreakpoint" else "",
            process_name=breakpoint_as_dict['ProcessName'] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else "",
            procedure=breakpoint_as_dict['Procedure'] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else "",
            line_number=breakpoint_as_dict['LineNumber'] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else "",
            object_name=breakpoint_as_dict['ObjectName'] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else "",
            object_type=breakpoint_as_dict['ObjectType'] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else "",
            lock_mode=breakpoint_as_dict['LockMode'] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else ""
        )

    @property
    def breakpoint_type(self) -> str:
        return self._type

    @property
    def breakpoint_id(self) -> int:
        return self._id

    @property
    def enabled(self) -> bool:
        return self._enabled
        
    @property
    def hitmode(self) -> str:
        return self._hitmode
        
    @property
    def hitcount(self) -> int:
        return self._hitcount
        
    @property
    def expression(self) -> str:
        return self._expression
        
    @property
    def variable_name(self) -> str:
        return self._variable_name
        
    @property
    def process_name(self) -> str:
        return self._process_name
        
    @property
    def procedure(self) -> str:
        return self._procedure
        
    @property
    def line_number(self) -> int:
        return self._line_number
        
    @property
    def object_name(self) -> str:
        return self._object_name
        
    @property
    def object_type(self) -> str:
        return self._object_type
        
    @property
    def lock_mode(self) -> str:
        return self._lock_mode

    @property
    def body(self) -> str:
        return self._construct_body()

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @hitmode.setter
    def hitmode(self, value: str):
        self._hitmode = value

    @expression.setter
    def expression(self, value: str):
        self._expression = value

    @variable_name.setter
    def variable_name(self, value: str):
        self._variable_name = value

    @process_name.setter
    def process_name(self, value: str):
        self._process_name = value

    @procedure.setter
    def procedure(self, value: str):
        self._procedure = value

    @line_number.setter
    def line_number(self, value: str):
        self._line_number = value

    @object_name.setter
    def object_name(self, value: str):
        self._object_name = value

    @object_type.setter
    def object_type(self, value: str):
        self._object_type = value

    @lock_mode.setter
    def lock_mode(self, value: str):
        self._lock_mode = value


    def _construct_body(self, **kwargs) -> str:
        body_as_dict = {
            '@odata.type': "#ibm.tm1.api.v1." + self._type,
            'ID': self._id,
            'Enabled': self._enabled,
            'HitMode': self._hitmode,
            'Expression': self._expression
        }

        if self._type == 'ProcessDebugContextDataBreakpoint':
            body_as_dict['VariableName'] = self._variable_name
        elif self._type == 'ProcessDebugContextLineBreakpoint':
            body_as_dict['ProcessName'] = self._process_name
            body_as_dict['Procedure'] = self._procedure
            body_as_dict['LineNumber'] = self._line_number
        elif self._type == 'ProcessDebugContextLockBreakpoint':
            body_as_dict['ObjectName'] = self._object_name
            body_as_dict['ObjectType'] = self._object_type
            body_as_dict['LockMode'] = self._lock_mode

        return json.dumps(body_as_dict, ensure_ascii=False)
