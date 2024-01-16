# -*- coding: utf-8 -*-

import json
import re
from typing import Optional, Iterable, Dict, List, Union

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils import verify_version


class Process(TM1Object):
    """ Abstraction of a TM1 Process.

        IMPORTANT. doesn't work with Processes that were generated through the Wizard
    """

    """ the auto_generated_string code is required to be in all code-tabs. """
    BEGIN_GENERATED_STATEMENTS = "#****Begin: Generated Statements***"
    END_GENERATED_STATEMENTS = "#****End: Generated Statements****"
    AUTO_GENERATED_STATEMENTS = "{}\r\n{}\r\n".format(BEGIN_GENERATED_STATEMENTS, END_GENERATED_STATEMENTS)
    MAX_STATEMENTS = 16_380
    MAX_STATEMENTS_POST_11_8_015 = 100_000

    @staticmethod
    def max_statements(version: str):
        if verify_version(required_version="11.8.015", version=version):
            return Process.MAX_STATEMENTS_POST_11_8_015

        return Process.MAX_STATEMENTS

    @staticmethod
    def add_generated_string_to_code(code: str) -> str:
        pattern = r"(?s)#\*\*\*\*Begin: Generated Statements(.*)#\*\*\*\*End: Generated Statements\*\*\*\*"
        if re.search(pattern=pattern, string=code):
            return code
        else:
            return Process.AUTO_GENERATED_STATEMENTS + code

    def __init__(self,
                 name: str,
                 has_security_access: Optional[bool] = False,
                 ui_data: str = "CubeAction=1511\fDataAction=1503\fCubeLogChanges=0\f",
                 parameters: Iterable = None,
                 variables: Iterable = None,
                 variables_ui_data: Iterable = None,
                 prolog_procedure: str = '',
                 metadata_procedure: str = '',
                 data_procedure: str = '',
                 epilog_procedure: str = '',
                 datasource_type: str = 'None',
                 datasource_ascii_decimal_separator: str = '.',
                 datasource_ascii_delimiter_char: str = ';',
                 datasource_ascii_delimiter_type: str = 'Character',
                 datasource_ascii_header_records: int = 1,
                 datasource_ascii_quote_character: str = '',
                 datasource_ascii_thousand_separator: str = ',',
                 datasource_data_source_name_for_client: str = '',
                 datasource_data_source_name_for_server: str = '',
                 datasource_password: str = '',
                 datasource_user_name: str = '',
                 datasource_query: str = '',
                 datasource_uses_unicode: bool = True,
                 datasource_view: str = '',
                 datasource_subset: str = ''):
        """ Default construcor

        :param name: name of the process - mandatory
        :param has_security_access:
        :param ui_data:
        :param parameters:
        :param variables:
        :param variables_ui_data:
        :param prolog_procedure:
        :param metadata_procedure:
        :param data_procedure:
        :param epilog_procedure:
        :param datasource_type:
        :param datasource_ascii_decimal_separator:
        :param datasource_ascii_delimiter_char:
        :param datasource_ascii_delimiter_type:
        :param datasource_ascii_header_records:
        :param datasource_ascii_quote_character:
        :param datasource_ascii_thousand_separator:
        :param datasource_data_source_name_for_client:
        :param datasource_data_source_name_for_server:
        :param datasource_password:
        :param datasource_user_name:
        :param datasource_query:
        :param datasource_uses_unicode:
        :param datasource_view:
        :param datasource_subset:
        """
        self._name = name
        self._has_security_access = has_security_access
        self._ui_data = ui_data
        self._parameters = list(parameters) if parameters else []
        self._variables = list(variables) if variables else []
        if variables_ui_data:
            # Handle encoding issue in variable_ui_data for async requests
            self._variables_ui_data = [entry.replace("€", "\f") for entry in variables_ui_data]
        else:
            self._variables_ui_data = []
        self._prolog_procedure = Process.add_generated_string_to_code(prolog_procedure)
        self._metadata_procedure = Process.add_generated_string_to_code(metadata_procedure)
        self._data_procedure = Process.add_generated_string_to_code(data_procedure)
        self._epilog_procedure = Process.add_generated_string_to_code(epilog_procedure)
        self._datasource_type = datasource_type
        self._datasource_ascii_decimal_separator = datasource_ascii_decimal_separator
        self._datasource_ascii_delimiter_char = datasource_ascii_delimiter_char
        self._datasource_ascii_delimiter_type = datasource_ascii_delimiter_type
        self._datasource_ascii_header_records = datasource_ascii_header_records
        self._datasource_ascii_quote_character = datasource_ascii_quote_character
        self._datasource_ascii_thousand_separator = datasource_ascii_thousand_separator
        self._datasource_data_source_name_for_client = datasource_data_source_name_for_client
        self._datasource_data_source_name_for_server = datasource_data_source_name_for_server
        self._datasource_password = datasource_password
        self._datasource_user_name = datasource_user_name
        self._datasource_query = datasource_query
        self._datasource_uses_unicode = datasource_uses_unicode
        self._datasource_view = datasource_view
        self._datasource_subset = datasource_subset

    @classmethod
    def from_json(cls, process_as_json: str) -> 'Process':
        """
        :param process_as_json: response of /Processes('x')?$expand=*
        :return: an instance of this class
        """
        process_as_dict = json.loads(process_as_json)
        return cls.from_dict(process_as_dict)

    @classmethod
    def from_dict(cls, process_as_dict: Dict) -> 'Process':
        """
        :param process_as_dict: Dictionary, process as dictionary
        :return: an instance of this class
        """
        return cls(name=process_as_dict['Name'],
                   has_security_access=process_as_dict['HasSecurityAccess'],
                   ui_data=process_as_dict['UIData'],
                   parameters=process_as_dict['Parameters'],
                   variables=process_as_dict['Variables'],
                   variables_ui_data=process_as_dict['VariablesUIData'],
                   prolog_procedure=process_as_dict['PrologProcedure'],
                   metadata_procedure=process_as_dict['MetadataProcedure'],
                   data_procedure=process_as_dict['DataProcedure'],
                   epilog_procedure=process_as_dict['EpilogProcedure'],
                   datasource_type=process_as_dict['DataSource'].get('Type', ''),
                   datasource_ascii_decimal_separator=process_as_dict['DataSource'].get('asciiDecimalSeparator', ''),
                   datasource_ascii_delimiter_char=process_as_dict['DataSource'].get('asciiDelimiterChar', ''),
                   datasource_ascii_delimiter_type=process_as_dict['DataSource'].get('asciiDelimiterType', ''),
                   datasource_ascii_header_records=process_as_dict['DataSource'].get('asciiHeaderRecords', ''),
                   datasource_ascii_quote_character=process_as_dict['DataSource'].get('asciiQuoteCharacter', ''),
                   datasource_ascii_thousand_separator=process_as_dict['DataSource'].get('asciiThousandSeparator', ''),
                   datasource_data_source_name_for_client=process_as_dict['DataSource'].get('dataSourceNameForClient',
                                                                                            ''),
                   datasource_data_source_name_for_server=process_as_dict['DataSource'].get('dataSourceNameForServer',
                                                                                            ''),
                   datasource_password=process_as_dict['DataSource'].get('password', ''),
                   datasource_user_name=process_as_dict['DataSource'].get('userName', ''),
                   datasource_query=process_as_dict['DataSource'].get('query', ''),
                   datasource_uses_unicode=process_as_dict['DataSource'].get('usesUnicode', ''),
                   datasource_view=process_as_dict['DataSource'].get('view', ''),
                   datasource_subset=process_as_dict['DataSource'].get('subset', ''))

    @property
    def body(self) -> str:
        return self._construct_body()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def has_security_access(self) -> bool:
        return self._has_security_access

    @has_security_access.setter
    def has_security_access(self, value: bool):
        self._has_security_access = value

    @property
    def variables(self) -> List:
        return self._variables

    @property
    def parameters(self) -> List:
        return self._parameters

    @property
    def prolog_procedure(self) -> str:
        return self._prolog_procedure

    @prolog_procedure.setter
    def prolog_procedure(self, value: str):
        self._prolog_procedure = Process.add_generated_string_to_code(value)

    @property
    def metadata_procedure(self) -> str:
        return self._metadata_procedure

    @metadata_procedure.setter
    def metadata_procedure(self, value: str):
        self._metadata_procedure = Process.add_generated_string_to_code(value)

    @property
    def data_procedure(self) -> str:
        return self._data_procedure

    @data_procedure.setter
    def data_procedure(self, value: str):
        self._data_procedure = Process.add_generated_string_to_code(value)

    @property
    def epilog_procedure(self) -> str:
        return self._epilog_procedure

    @epilog_procedure.setter
    def epilog_procedure(self, value: str):
        self._epilog_procedure = Process.add_generated_string_to_code(value)

    @property
    def datasource_type(self) -> str:
        return self._datasource_type

    @datasource_type.setter
    def datasource_type(self, value: str):
        self._datasource_type = value

    @property
    def datasource_ascii_decimal_separator(self) -> str:
        return self._datasource_ascii_decimal_separator

    @datasource_ascii_decimal_separator.setter
    def datasource_ascii_decimal_separator(self, value: str):
        self._datasource_ascii_decimal_separator = value

    @property
    def datasource_ascii_delimiter_char(self) -> str:
        return self._datasource_ascii_delimiter_char

    @datasource_ascii_delimiter_char.setter
    def datasource_ascii_delimiter_char(self, value: str):
        self._datasource_ascii_delimiter_char = value

    @property
    def datasource_ascii_delimiter_type(self) -> str:
        return self._datasource_ascii_delimiter_type

    @datasource_ascii_delimiter_type.setter
    def datasource_ascii_delimiter_type(self, value: str):
        self._datasource_ascii_delimiter_type = value

    @property
    def datasource_ascii_header_records(self) -> int:
        return self._datasource_ascii_header_records

    @datasource_ascii_header_records.setter
    def datasource_ascii_header_records(self, value: int):
        self._datasource_ascii_header_records = value

    @property
    def datasource_ascii_quote_character(self) -> str:
        return self._datasource_ascii_quote_character

    @datasource_ascii_quote_character.setter
    def datasource_ascii_quote_character(self, value: str):
        self._datasource_ascii_quote_character = value

    @property
    def datasource_ascii_thousand_separator(self) -> str:
        return self._datasource_ascii_thousand_separator

    @datasource_ascii_thousand_separator.setter
    def datasource_ascii_thousand_separator(self, value: str):
        self._datasource_ascii_thousand_separator = value

    @property
    def datasource_data_source_name_for_client(self) -> str:
        return self._datasource_data_source_name_for_client

    @datasource_data_source_name_for_client.setter
    def datasource_data_source_name_for_client(self, value: str):
        self._datasource_data_source_name_for_client = value

    @property
    def datasource_data_source_name_for_server(self) -> str:
        return self._datasource_data_source_name_for_server

    @datasource_data_source_name_for_server.setter
    def datasource_data_source_name_for_server(self, value: str):
        self._datasource_data_source_name_for_server = value

    @property
    def datasource_password(self) -> str:
        return self._datasource_password

    @datasource_password.setter
    def datasource_password(self, value: str):
        self._datasource_password = value

    @property
    def datasource_user_name(self) -> str:
        return self._datasource_user_name

    @datasource_user_name.setter
    def datasource_user_name(self, value: str):
        self._datasource_user_name = value

    @property
    def datasource_query(self) -> str:
        return self._datasource_query

    @datasource_query.setter
    def datasource_query(self, value: str):
        self._datasource_query = value

    @property
    def datasource_uses_unicode(self) -> bool:
        return self._datasource_uses_unicode

    @datasource_uses_unicode.setter
    def datasource_uses_unicode(self, value: bool):
        self._datasource_uses_unicode = value

    @property
    def datasource_view(self) -> str:
        return self._datasource_view

    @datasource_view.setter
    def datasource_view(self, value: str):
        self._datasource_view = value

    @property
    def datasource_subset(self) -> str:
        return self._datasource_subset

    @datasource_subset.setter
    def datasource_subset(self, value: str):
        self._datasource_subset = value

    def add_variable(self, name: str, variable_type: str):
        """ add variable to the process

        :param name: -
        :param variable_type: 'String' or 'Numeric'
        :return:
        """
        # variable consists of actual variable and UI-Information ('ignore','other', etc.)
        # 1. handle Variable info
        variable = {'Name': name,
                    'Type': variable_type,
                    'Position': len(self._variables) + 1,
                    'StartByte': 0,
                    'EndByte': 0}
        self._variables.append(variable)
        # 2. handle UI info
        var_type = 33 if variable_type == 'Numeric' else 32
        # '\f' !
        variable_ui_data = 'VarType=' + str(var_type) + '\f' + 'ColType=' + str(827) + '\f'
        """
        mapping VariableUIData:
            VarType 33 -> Numeric
            VarType 32 -> String
            ColType 827 -> Other
        """
        self._variables_ui_data.append(variable_ui_data)

    def remove_variable(self, name: str):
        for variable in self.variables[:]:
            if variable['Name'] == name:
                vuid = self._variables_ui_data[self._variables.index(variable)]
                self._variables_ui_data.remove(vuid)
                self._variables.remove(variable)

    def add_parameter(self, name: str, prompt: str, value: Union[str, int, float],
                      parameter_type: Optional[str] = None):
        """
        
        :param name: 
        :param prompt: 
        :param value: 
        :param parameter_type: introduced in TM1 11 REST API, therefor optional. if Not given type is derived from value
        :return: 
        """
        if not parameter_type:
            parameter_type = 'String' if isinstance(value, str) else 'Numeric'
        parameter = {'Name': name,
                     'Prompt': prompt,
                     'Value': value,
                     'Type': parameter_type}
        self._parameters.append(parameter)

    def remove_parameter(self, name: str):
        for parameter in self.parameters[:]:
            if parameter['Name'] == name:
                self._parameters.remove(parameter)

    def drop_parameter_types(self):
        for p in range(len(self.parameters)):
            if 'Type' in self.parameters[p]:
                del self.parameters[p]['Type']

    # construct self.body (json) from the class-attributes
    def _construct_body(self) -> str:
        # general parameters
        body_as_dict = {
            'Name': self._name,
            'PrologProcedure': self._prolog_procedure,
            'MetadataProcedure': self._metadata_procedure,
            'DataProcedure': self._data_procedure,
            'EpilogProcedure': self._epilog_procedure,
            'HasSecurityAccess': self._has_security_access,
            'UIData': self._ui_data,
            'DataSource': {},
            'Parameters': self._parameters,
            'Variables': self._variables,
            'VariablesUIData': self._variables_ui_data}

        # specific parameters (depending on datasource type)
        if self._datasource_type == 'ASCII':
            body_as_dict['DataSource'] = {
                "Type": self._datasource_type,
                "asciiDecimalSeparator": self._datasource_ascii_decimal_separator,
                "asciiDelimiterChar": self._datasource_ascii_delimiter_char,
                "asciiDelimiterType": self._datasource_ascii_delimiter_type,
                "asciiHeaderRecords": self._datasource_ascii_header_records,
                "asciiQuoteCharacter": self._datasource_ascii_quote_character,
                "asciiThousandSeparator": self._datasource_ascii_thousand_separator,
                "dataSourceNameForClient": self._datasource_data_source_name_for_client,
                "dataSourceNameForServer": self._datasource_data_source_name_for_server
            }
            if self._datasource_ascii_delimiter_type == 'FixedWidth':
                del body_as_dict['DataSource']['asciiDelimiterChar']
        elif self._datasource_type == 'None':
            body_as_dict['DataSource'] = {
                "Type": "None"
            }
        elif self._datasource_type == 'ODBC':
            body_as_dict['DataSource'] = {
                "Type": self._datasource_type,
                "dataSourceNameForClient": self._datasource_data_source_name_for_client,
                "dataSourceNameForServer": self._datasource_data_source_name_for_server,
                "userName": self._datasource_user_name,
                "password": self._datasource_password,
                "query": self._datasource_query,
                "usesUnicode": self._datasource_uses_unicode
            }
        elif self._datasource_type == 'TM1CubeView':
            body_as_dict['DataSource'] = {
                "Type": self._datasource_type,
                "dataSourceNameForClient": self._datasource_data_source_name_for_server,
                "dataSourceNameForServer": self._datasource_data_source_name_for_server,
                "view": self._datasource_view
            }

        elif self._datasource_type == 'TM1DimensionSubset':
            body_as_dict['DataSource'] = {
                "Type": self._datasource_type,
                "dataSourceNameForClient": self._datasource_data_source_name_for_server,
                "dataSourceNameForServer": self._datasource_data_source_name_for_server,
                "subset": self._datasource_subset
            }
        return json.dumps(body_as_dict, ensure_ascii=False)
