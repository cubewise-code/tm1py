# -*- coding: utf-8 -*-

import json
import time
import uuid
from typing import List, Dict, Tuple, Iterable

from requests import Response

from TM1py.Exceptions.Exceptions import TM1pyRestException
from TM1py.Objects.Process import Process
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url, require_admin
from TM1py.Utils.Utils import require_version


class ProcessService(ObjectService):
    """ Service to handle Object Updates for TI Processes
    
    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, name_process: str, **kwargs) -> Process:
        """ Get a process from TM1 Server
    
        :param name_process:
        :return: Instance of the TM1py.Process
        """
        url = format_url(
            "/api/v1/Processes('{}')?$select=*,UIData,VariablesUIData,"
            "DataSource/dataSourceNameForServer,"
            "DataSource/dataSourceNameForClient,"
            "DataSource/asciiDecimalSeparator,"
            "DataSource/asciiDelimiterChar,"
            "DataSource/asciiDelimiterType,"
            "DataSource/asciiHeaderRecords,"
            "DataSource/asciiQuoteCharacter,"
            "DataSource/asciiThousandSeparator,"
            "DataSource/view,"
            "DataSource/query,"
            "DataSource/userName,"
            "DataSource/password,"
            "DataSource/usesUnicode,"
            "DataSource/subset", name_process)
        response = self._rest.GET(url, **kwargs)
        return Process.from_dict(response.json())

    def get_all(self, skip_control_processes: bool = False, **kwargs) -> List[Process]:
        """ Get a processes from TM1 Server
    
        :skip_control_processes: bool, True to exclude processes that begin with "}" or "{"
        :return: List, instances of the TM1py.Process
        """
        model_process_filter = "&$filter=startswith(Name,'}') eq false and startswith(Name,'{') eq false"

        url = "/api/v1/Processes?$select=*,UIData,VariablesUIData," \
              "DataSource/dataSourceNameForServer," \
              "DataSource/dataSourceNameForClient," \
              "DataSource/asciiDecimalSeparator," \
              "DataSource/asciiDelimiterChar," \
              "DataSource/asciiDelimiterType," \
              "DataSource/asciiHeaderRecords," \
              "DataSource/asciiQuoteCharacter," \
              "DataSource/asciiThousandSeparator," \
              "DataSource/view," \
              "DataSource/query," \
              "DataSource/userName," \
              "DataSource/password," \
              "DataSource/usesUnicode," \
              "DataSource/subset{}".format(model_process_filter if skip_control_processes else "")

        response = self._rest.GET(url, **kwargs)
        response_as_dict = response.json()
        return [Process.from_dict(p) for p in response_as_dict['value']]

    def get_all_names(self, skip_control_processes: bool = False, **kwargs) -> List[str]:
        """ Get List with all process names from TM1 Server
        
        :skip_control_processes: bool, True to exclude processes that begin with "}" or "{"
        :Returns:
            List of Strings
        """
        model_process_filter = "&$filter=startswith(Name,'}') eq false and startswith(Name,'{') eq false"
        url = "/api/v1/Processes?$select=Name{}".format(model_process_filter if skip_control_processes else "")
        
        response = self._rest.GET(url, **kwargs)
        processes = list(process['Name'] for process in response.json()['value'])
        return processes

    def search_string_in_code(self, search_string: str, skip_control_processes: bool=False, **kwargs) -> List[str]:
        """ Ask TM1 Server for list of process names that contain string anywhere in code tabs: Prolog,Metadata,Data,Epilog
        will not search DataSource, Parameters, Variables, or Attributes

        :param skip_control_processes: bool, True to exclude processes that begin with "}" or "{"
        :param skip_control_processe
        """
        model_process_filter = "&$filter=startswith(Name,'}') eq false and startswith(Name,'{') eq false"
        url = format_url("/api/v1/Processes?$select=Name&$filter=" \
                         "contains(toupper(PrologProcedure),toupper('{}')) " \
                         "or contains(toupper(MetadataProcedure),toupper('{}')) " \
                         "or contains(toupper(DataProcedure),toupper('{}')) " \
                         "or contains(toupper(EpilogProcedure),toupper('{}'))",
                         search_string, search_string, search_string, search_string
            ) + "{}".format(model_process_filter if skip_control_processes else "")
        response = self._rest.GET(url, **kwargs)
        processes = list(process['Name'] for process in response.json()['value'])
        return processes

    def search_string_in_name(self, name_startswith: str = None, name_contains: Iterable = None,
                              name_contains_operator: str = 'and', **kwargs) -> List[str]:
        """ Ask TM1 Server for list of process names that contain or start with string

        :param name_startswith: str, process name begins with (case insensitive)
        :param name_contains: iterable, found anywhere in name (case insensitive)
        :param name_contains_operator: 'and' or 'or'
        """
        name_contains_operator = name_contains_operator.strip().lower()
        if name_contains_operator not in ("and", "or"):
            raise ValueError("'name_contains_operator' must be either 'AND' or 'OR'")

        url = "/api/v1/Processes?$select=Name"
        name_filters = []

        if name_startswith:
            name_filters.append(format_url("startswith(toupper(Name),toupper('{}'))", name_startswith))

        if name_contains:
            if isinstance(name_contains, str):
                name_filters.append(format_url("contains(toupper(Name),toupper('{}'))", name_contains))

            elif isinstance(name_contains, Iterable):
                name_contains_filters = [format_url("contains(toupper(Name),toupper('{}'))", wildcard)
                                         for wildcard in name_contains]
                name_filters.append("({})".format(f" {name_contains_operator} ".join(name_contains_filters)))

            else:
                raise ValueError("'name_contains' must be str or iterable")

        url += "&$filter={}".format(f" and ".join(name_filters))
        response = self._rest.GET(url, **kwargs)
        return list(process['Name'] for process in response.json()['value'])
    
    def create(self, process: Process, **kwargs) -> Response:
        """ Create a new process on TM1 Server

        :param process: Instance of TM1py.Process class
        :return: Response
        """
        url = "/api/v1/Processes"
        # Adjust process body if TM1 version is lower than 11 due to change in Process Parameters structure
        # https://www.ibm.com/developerworks/community/forums/html/topic?id=9188d139-8905-4895-9229-eaaf0e7fa683
        if int(self.version[0:2]) < 11:
            process.drop_parameter_types()
        response = self._rest.POST(url, process.body, **kwargs)
        return response

    def update(self, process: Process, **kwargs) -> Response:
        """ Update an existing Process on TM1 Server
    
        :param process: Instance of TM1py.Process class
        :return: Response
        """
        url = format_url("/api/v1/Processes('{}')", process.name)
        # Adjust process body if TM1 version is lower than 11 due to change in Process Parameters structure
        # https://www.ibm.com/developerworks/community/forums/html/topic?id=9188d139-8905-4895-9229-eaaf0e7fa683
        if int(self.version[0:2]) < 11:
            process.drop_parameter_types()
        response = self._rest.PATCH(url, process.body, **kwargs)
        return response

    def update_or_create(self, process: Process, **kwargs) -> Response:
        """ Update or Create a Process on TM1 Server

        :param process: Instance of TM1py.Process class
        :return: Response
        """
        if self.exists(name=process.name, **kwargs):
            return self.update(process=process, **kwargs)

        return self.create(process=process, **kwargs)

    def delete(self, name: str, **kwargs) -> Response:
        """ Delete a process in TM1
        
        :param name: 
        :return: Response
        """
        url = format_url("/api/v1/Processes('{}')", name)
        response = self._rest.DELETE(url, **kwargs)
        return response

    def exists(self, name: str, **kwargs) -> bool:
        """ Check if Process exists.
        
        :param name: 
        :return: 
        """
        url = format_url("/api/v1/Processes('{}')", name)
        return self._exists(url, **kwargs)

    def compile(self, name: str, **kwargs) -> List:
        """ Compile a Process. Return List of Syntax errors.
        
        :param name: 
        :return: 
        """
        url = format_url("/api/v1/Processes('{}')/tm1.Compile", name)
        response = self._rest.POST(url, **kwargs)
        syntax_errors = response.json()["value"]
        return syntax_errors

    def compile_process(self, process: Process, **kwargs) -> List:
        """ Compile a Process. Return List of Syntax errors.

        :param process:
        :return:
        """
        url = "/api/v1/CompileProcess"

        payload = json.loads('{"Process":' + process.body + '}')

        response = self._rest.POST(
            url=url,
            data=json.dumps(payload, ensure_ascii=False),
            **kwargs)

        syntax_errors = response.json()["value"]
        return syntax_errors

    def execute(self, process_name: str, parameters: Dict = None, timeout: float = None,
                cancel_at_timeout: bool = False, **kwargs) -> Response:
        """ Ask TM1 Server to execute a process. Call with parameter names as keyword arguments:
        tm1.processes.execute("Bedrock.Server.Wait", pLegalEntity="UK01")

        :param process_name:
        :param parameters: Deprecated! dictionary, e.g. {"Parameters": [ { "Name": "pLegalEntity", "Value": "UK01" }] }
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :return:
        """
        url = format_url("/api/v1/Processes('{}')/tm1.Execute", process_name)
        if not parameters:
            if kwargs:
                parameters = {"Parameters": []}
                for parameter_name, parameter_value in kwargs.items():
                    parameters["Parameters"].append({"Name": parameter_name, "Value": parameter_value})
            else:
                parameters = {}
        return self._rest.POST(url=url, data=json.dumps(parameters, ensure_ascii=False), timeout=timeout,
                               cancel_at_timeout=cancel_at_timeout, **kwargs)

    @require_version(version="11.3")
    def execute_process_with_return(self, process: Process, timeout: float = None, cancel_at_timeout: bool = False,
                                    **kwargs) -> Tuple[bool, str, str]:
        """Run unbound TI code directly.

        :param process: a TI Process Object
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param kwargs: dictionary of process parameters and values
        :return: success (boolean), status (String), error_log_file (String)
        """
        url = "/api/v1/ExecuteProcessWithReturn?$expand=*"
        if kwargs:
            for parameter_name, parameter_value in kwargs.items():
                process.remove_parameter(name=parameter_name)
                process.add_parameter(name=parameter_name,
                                      prompt=parameter_name,
                                      value=parameter_value)

        payload = json.loads("{\"Process\":" + process.body + "}")

        response = self._rest.POST(
            url=url,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=timeout,
            cancel_at_timeout=cancel_at_timeout,
            **kwargs)

        execution_summary = response.json()

        success = execution_summary["ProcessExecuteStatusCode"] == "CompletedSuccessfully"
        status = execution_summary["ProcessExecuteStatusCode"]
        error_log_file = None if execution_summary["ErrorLogFile"] is None else execution_summary["ErrorLogFile"][
            "Filename"]
        return success, status, error_log_file

    def execute_with_return(self, process_name: str, timeout: float = None, cancel_at_timeout: bool = False,
                            **kwargs) -> Tuple[bool, str, str]:
        """ Ask TM1 Server to execute a process.
        pass process parameters as keyword arguments to this function. E.g:

        self.tm1.processes.execute_with_return(
            process_name="Bedrock.Server.Wait",
            pWaitSec=2)

        :param process_name: name of the TI process
        :param timeout: Number of seconds that the client will wait to receive the first byte.
        :param cancel_at_timeout: Abort operation in TM1 when timeout is reached
        :param kwargs: dictionary of process parameters and values
        :return: success (boolean), status (String), error_log_file (String)
        """
        url = format_url("/api/v1/Processes('{}')/tm1.ExecuteWithReturn?$expand=*", process_name)
        parameters = dict()
        if kwargs:
            parameters = {"Parameters": []}
            for parameter_name, parameter_value in kwargs.items():
                parameters["Parameters"].append({"Name": parameter_name, "Value": parameter_value})

        response = self._rest.POST(
            url=url,
            data=json.dumps(parameters, ensure_ascii=False),
            timeout=timeout,
            cancel_at_timeout=cancel_at_timeout,
            **kwargs)
        execution_summary = response.json()
        success = execution_summary["ProcessExecuteStatusCode"] == "CompletedSuccessfully"
        status = execution_summary["ProcessExecuteStatusCode"]
        error_log_file = None if execution_summary["ErrorLogFile"] is None else execution_summary["ErrorLogFile"][
            "Filename"]
        return success, status, error_log_file

    @require_admin
    def execute_ti_code(self, lines_prolog: Iterable[str], lines_epilog: Iterable[str] = None, **kwargs) -> Response:
        """ Execute lines of code on the TM1 Server

            :param lines_prolog: list - where each element is a valid statement of TI code.
            :param lines_epilog: list - where each element is a valid statement of TI code.
        """
        process_name = "".join(['}TM1py', str(uuid.uuid4())])
        p = Process(name=process_name,
                    prolog_procedure=Process.AUTO_GENERATED_STATEMENTS + '\r\n'.join(lines_prolog),
                    epilog_procedure=Process.AUTO_GENERATED_STATEMENTS + '\r\n'.join(
                        lines_epilog) if lines_epilog else '')
        self.create(p, **kwargs)
        try:
            return self.execute(process_name, **kwargs)
        except TM1pyRestException as e:
            raise e
        finally:
            self.delete(process_name, **kwargs)

    def get_error_log_file_content(self, file_name: str, **kwargs) -> str:
        """ Get content of error log file (e.g. TM1ProcessError_20180926213819_65708356_979b248b-232e622c6.log)

        :param file_name: name of the error log file in the TM1 log directory
        :return: String, content of the file
        """
        url = format_url("/api/v1/ErrorLogFiles('{}')/Content", file_name)
        response = self._rest.GET(url=url, **kwargs)
        return response.text

    def get_processerrorlogs(self, process_name: str, **kwargs) -> List:
        """ Get all ProcessErrorLog entries for a process

        :param process_name: name of the process
        :return: list - Collection of ProcessErrorLogs
        """
        url = format_url("/api/v1/Processes('{}')/ErrorLogs", process_name)
        response = self._rest.GET(url=url, **kwargs)
        return response.json()['value']

    def get_last_message_from_processerrorlog(self, process_name: str, **kwargs) -> str:
        """ Get the latest ProcessErrorLog from a process entity

            :param process_name: name of the process
            :return: String - the errorlog, e.g.:  "Error: Data procedure line (9): Invalid key:
            Dimension Name: "Product", Element Name (Key): "ProductA""
        """
        logs_as_list = self.get_processerrorlogs(process_name, **kwargs)
        if len(logs_as_list) > 0:
            timestamp = logs_as_list[-1]['Timestamp']
            url = format_url("/api/v1/Processes('{}')/ErrorLogs('{}')/Content", process_name, timestamp)
            # response is plain text - due to entity type Edm.Stream
            response = self._rest.GET(url=url, **kwargs)
            return response.text

    def debug_process(self, process_name: str, timeout: float = None, **kwargs) -> Dict:
        raw_url = "/api/v1/Processes('{}')/tm1.Debug?$expand=Breakpoints," \
                  "Thread,CallStack($expand=Variables,Process($select=Name))"
        url = format_url(raw_url, process_name)

        parameters = dict()
        if kwargs:
            parameters = {"Parameters": []}
            for parameter_name, parameter_value in kwargs.items():
                parameters["Parameters"].append({"Name": parameter_name, "Value": parameter_value})

        response = self._rest.POST(
            url,
            data=json.dumps(parameters, ensure_ascii=False),
            timeout=timeout,
            **kwargs)
        return response.json()

    def debug_step_over(self, debug_id: str, **kwargs) -> Dict:
        url = format_url("/api/v1/ProcessDebugContexts('{}')/tm1.StepOver", debug_id)
        self._rest.POST(url, **kwargs)

        # digest time  necessary for TM1 <= 11.8
        # ToDo: remove in later versions of TM1 once issue in TM1 server is resolved
        time.sleep(0.1)

        raw_url = "/api/v1/ProcessDebugContexts('{}')?$expand=Breakpoints," \
                  "Thread,CallStack($expand=Variables,Process($select=Name))"
        url = format_url(raw_url, debug_id)
        response = self._rest.GET(url, **kwargs)

        return response.json()

    def debug_step_out(self, debug_id: str, **kwargs) -> Dict:
        url = format_url("/api/v1/ProcessDebugContexts('{}')/tm1.StepOut", debug_id)
        self._rest.POST(url, **kwargs)

        # digest time  necessary for TM1 <= 11.8
        # ToDo: remove in later versions of TM1 once issue in TM1 server is resolved
        time.sleep(0.1)

        raw_url = "/api/v1/ProcessDebugContexts('{}')?$expand=Breakpoints," \
                  "Thread,CallStack($expand=Variables,Process($select=Name))"
        url = format_url(raw_url, debug_id)
        response = self._rest.GET(url, **kwargs)

        return response.json()
