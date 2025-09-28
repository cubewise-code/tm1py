# -*- coding: utf-8 -*-
import json
from enum import Enum
from typing import Dict, Union

from TM1py.Objects.TM1Object import TM1Object


class HitMode(Enum):
    BREAK_ALWAYS = "BreakAlways"
    BREAK_EQUAL = "BreakEqual"
    BREAK_GREATER_OR_EQUAL = "BreakGreaterOrEqual"

    def __str__(self):
        return self.value

    @classmethod
    def _missing_(cls, value: str):
        for member in cls:
            if member.value.lower() == value.replace(" ", "").lower():
                return member

        # default
        raise ValueError(f"Invalid HitMode: '{value}'")


class BreakPointType(Enum):
    # A breakpoint that pauses execution when the named variable is written to
    PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT = "ProcessDebugContextDataBreakpoint"
    # A breakpoint that pauses execution at a specific script line
    PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT = "ProcessDebugContextLineBreakpoint"
    # A breakpoint that pauses execution when an object lock is acquired.
    PROCESS_DEBUG_CONTEXT_LOCK_BREAK_POINT = "ProcessDebugContextLockBreakpoint"

    def __str__(self):
        return self.value

    @classmethod
    def _missing_(cls, value: str):
        for member in cls:
            if member.value.lower() == value.replace(" ", "").lower():
                return member

        # default
        raise ValueError(f"Invalid BreakPointType: '{value}'")


class ProcessDebugBreakpoint(TM1Object):
    """Abstraction of a TM1 Process Debug Breakpoint."""

    def __init__(
        self,
        breakpoint_id: int,
        breakpoint_type: Union[BreakPointType, str] = BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT,
        enabled: bool = True,
        hit_mode: Union[HitMode, str] = HitMode.BREAK_ALWAYS,
        hit_count: int = 0,
        expression: str = "",
        variable_name: str = "",
        process_name: str = "",
        procedure: str = "",
        line_number: int = 0,
        object_name: str = "",
        object_type: str = "",
        lock_mode: str = "",
    ):
        self._type = BreakPointType(breakpoint_type)
        self._id = breakpoint_id
        self._enabled = enabled
        self._hit_mode = HitMode(hit_mode)
        self._hit_count = hit_count
        self._expression = expression
        self._variable_name = variable_name
        self._process_name = process_name
        self._procedure = procedure
        self._line_number = line_number
        self._object_name = object_name
        self._object_type = object_type
        self._lock_mode = lock_mode

    @classmethod
    def from_dict(cls, breakpoint_as_dict: Dict) -> "ProcessDebugBreakpoint":
        """
        :param breakpoint_as_dict:
        :return: an instance of this class
        """
        breakpoint_type = breakpoint_as_dict["@odata.type"][16:]
        return cls(
            breakpoint_type=breakpoint_type,
            breakpoint_id=breakpoint_as_dict["ID"],
            enabled=breakpoint_as_dict["Enabled"],
            hit_mode=breakpoint_as_dict["HitMode"],
            hit_count=breakpoint_as_dict["HitCount"],
            expression=breakpoint_as_dict["Expression"],
            variable_name=(
                breakpoint_as_dict["VariableName"] if breakpoint_type == "ProcessDebugContextDataBreakpoint" else ""
            ),
            process_name=(
                breakpoint_as_dict["ProcessName"] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else ""
            ),
            procedure=breakpoint_as_dict["Procedure"] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else "",
            line_number=(
                breakpoint_as_dict["LineNumber"] if breakpoint_type == "ProcessDebugContextLineBreakpoint" else ""
            ),
            object_name=(
                breakpoint_as_dict["ObjectName"] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else ""
            ),
            object_type=(
                breakpoint_as_dict["ObjectType"] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else ""
            ),
            lock_mode=breakpoint_as_dict["LockMode"] if breakpoint_type == "ProcessDebugContextLockBreakpoint" else "",
        )

    @property
    def breakpoint_type(self) -> str:
        return str(self._type)

    @property
    def breakpoint_id(self) -> int:
        return self._id

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def hit_mode(self) -> str:
        return str(self._hit_mode)

    @property
    def hit_count(self) -> int:
        return self._hit_count

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
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @hit_mode.setter
    def hit_mode(self, value: Union[HitMode, str]):
        self._hit_mode = HitMode(value)

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

    def _construct_body(self) -> str:
        body_as_dict = {
            "@odata.type": "#ibm.tm1.api.v1." + str(self._type),
            "ID": self._id,
            "Enabled": self._enabled,
            "HitMode": str(self._hit_mode),
            "Expression": self._expression,
        }

        if self._type == BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT:
            body_as_dict["VariableName"] = self._variable_name

        elif self._type == BreakPointType.PROCESS_DEBUG_CONTEXT_LINE_BREAK_POINT:
            body_as_dict["ProcessName"] = self._process_name
            body_as_dict["Procedure"] = self._procedure
            body_as_dict["LineNumber"] = self._line_number

        elif self._type == BreakPointType.PROCESS_DEBUG_CONTEXT_LOCK_BREAK_POINT:
            body_as_dict["ObjectName"] = self._object_name
            body_as_dict["ObjectType"] = self._object_type
            body_as_dict["LockMode"] = self._lock_mode

        return body_as_dict
