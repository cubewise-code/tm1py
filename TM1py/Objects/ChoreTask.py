# -*- coding: utf-8 -*-

import collections
import json
from typing import Dict, List

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import format_url


class ChoreTask(TM1Object):
    """ Abstraction of a Chore Task
    
        A Chore task always conistst of
        - The step integer ID: it's order in the execution plan.
          1 to n, where n is the last Process in the Chore
        - The name of the process to execute
        - The parameters for the process
    
    """

    def __init__(self, step: int, process_name: str, parameters: List[Dict[str, str]]):
        """
        
        :param step: step in the execution order of the Chores' processes. 1 to n, where n the number of processes
        :param process_name: name of the process
        :param parameters: list of dictionaries with 'Name' and 'Value' property:
                            [{
                                'Name': '..',
                                'Value': '..'
                            },
                            ...
                            ]            
        """
        self._step = step
        self._process_name = process_name
        self._parameters = parameters

    @classmethod
    def from_dict(cls, chore_task_as_dict: Dict, step: int = None):
        if 'Process' in chore_task_as_dict:
            process_name = chore_task_as_dict['Process']['Name']
        else:
            # Extract "ProcessName" from "Processes('ProcessName')"
            process_name = chore_task_as_dict['Process@odata.bind'][11:-2]

        return cls(step=step if step is not None else int(chore_task_as_dict['Step']),
                   process_name=process_name,
                   parameters=[{'Name': p['Name'], 'Value': p['Value']} for p in chore_task_as_dict['Parameters']])

    @property
    def body_as_dict(self) -> Dict:
        body_as_dict = collections.OrderedDict()
        body_as_dict['Process@odata.bind'] = format_url("Processes('{}')", self._process_name)
        body_as_dict['Parameters'] = self._parameters
        return body_as_dict

    @property
    def step(self) -> int:
        return self._step

    @property
    def process_name(self) -> str:
        return self._process_name

    @property
    def parameters(self) -> List[Dict[str, str]]:
        return self._parameters

    @property
    def body(self) -> str:
        return json.dumps(self.body_as_dict, ensure_ascii=False)

    def __eq__(self, other: 'ChoreTask') -> bool:
        return self.process_name == other.process_name and self.parameters == other.parameters

    def __ne__(self, other: 'ChoreTask') -> bool:
        return self.process_name != other.process_name or self._parameters != other.parameters
