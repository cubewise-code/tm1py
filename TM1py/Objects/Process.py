# -*- coding: utf-8 -*-

import re
import json
from TM1py.Objects.TM1Object import TM1Object


class Process(TM1Object):
    """ Abstraction of a TM1 Process.

        IMPORTANT. doesn't work with Processes that were generated through the Wizard
    """

    """ the auto_generated_string code is required to be in all code-tabs. """
    begin_generated_statements = "#****Begin: Generated Statements***"
    end_generated_statements = "#****End: Generated Statements****"
    auto_generated_string = "{}\r\n{}\r\n".format(begin_generated_statements, end_generated_statements)

    @staticmethod
    def add_generated_string_to_code(code):
        pattern = r"#\*\*\*\*Begin: Generated Statements(?s)(.*)#\*\*\*\*End: Generated Statements\*\*\*\*"
        if re.search(pattern=pattern, string=code):
            return code
        else:
            return Process.auto_generated_string + code

    def __init__(self,
                 name,
                 has_security_access=False,
                 ui_data="CubeAction=1511€DataAction=1503€CubeLogChanges=0€",
                 parameters=None,
                 variables=None,
                 variables_ui_data=None,
                 prolog_procedure='',
                 metadata_procedure='',
                 data_procedure='',
                 epilog_procedure= '',
                 datasource_type='None',
                 datasource_ascii_decimal_separator='.',
                 datasource_ascii_delimiter_char=';',
                 datasource_ascii_delimiter_type='Character',
                 datasource_ascii_header_records=1,
                 datasource_ascii_quote_character='',
                 datasource_ascii_thousand_separator=',',
                 datasource_data_source_name_for_client='',
                 datasource_data_source_name_for_server='',
                 datasource_password='',
                 datasource_user_name='',
                 datasource_query='',
                 datasource_uses_unicode=True,
                 datasource_view='',
                 datasource_subset=''):
        """ Default construcor

        :param name: name of the process - mandatory
        :param others: all other parameters optional
        :return:
        """
        self._name = name
        self._has_security_access = has_security_access
        self._ui_data = ui_data
        self._parameters = list(parameters)if parameters else []
        self._variables = list(variables) if variables else []
        self._variables_ui_data = list(variables_ui_data) if variables_ui_data else []
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
    def from_json(cls, process_as_json):
        """
        :param process_as_json: response of /api/v1/Processes('x')?$expand=*
        :return: an instance of this class
        """
        process_as_dict = json.loads(process_as_json)
        return cls.from_dict(process_as_dict)

    @classmethod
    def from_dict(cls, process_as_dict):
        """
        :param process_as_json: Dictionary, process as dictionary
        :return: an instance of this class
        """
        f = lambda dict, key : dict[key] if key in dict else ''
        return cls(name=process_as_dict['Name'],
                   has_security_access=process_as_dict['HasSecurityAccess'],
                   ui_data=process_as_dict['UIData'],
                   parameters=process_as_dict['Parameters'],
                   variables=process_as_dict['Variables'],
                   variables_ui_data = process_as_dict['VariablesUIData'],
                   prolog_procedure=process_as_dict['PrologProcedure'],
                   metadata_procedure=process_as_dict['MetadataProcedure'],
                   data_procedure=process_as_dict['DataProcedure'],
                   epilog_procedure=process_as_dict['EpilogProcedure'],
                   datasource_type=f(process_as_dict['DataSource'], 'Type'),
                   datasource_ascii_decimal_separator=f(process_as_dict['DataSource'], 'asciiDecimalSeparator'),
                   datasource_ascii_delimiter_char=f(process_as_dict['DataSource'], 'asciiDelimiterChar'),
                   datasource_ascii_delimiter_type=f(process_as_dict['DataSource'], 'asciiDelimiterType'),
                   datasource_ascii_header_records=f(process_as_dict['DataSource'], 'asciiHeaderRecords'),
                   datasource_ascii_quote_character=f(process_as_dict['DataSource'], 'asciiQuoteCharacter'),
                   datasource_ascii_thousand_separator=f(process_as_dict['DataSource'], 'asciiThousandSeparator'),
                   datasource_data_source_name_for_client=f(process_as_dict['DataSource'], 'dataSourceNameForClient'),
                   datasource_data_source_name_for_server=f(process_as_dict['DataSource'], 'dataSourceNameForServer'),
                   datasource_password=f(process_as_dict['DataSource'], 'password'),
                   datasource_user_name=f(process_as_dict['DataSource'], 'userName'),
                   datasource_query=f(process_as_dict['DataSource'], 'query'),
                   datasource_uses_unicode=f(process_as_dict['DataSource'], 'usesUnicode'),
                   datasource_view=f(process_as_dict['DataSource'], 'view'),
                   datasource_subset=f(process_as_dict['DataSource'], 'subset'))

    @property
    def body(self):
        return self._construct_body()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def has_security_access(self):
        return self._has_security_access

    @has_security_access.setter
    def has_security_access(self, value):
        self._has_security_access = value

    @property
    def variables(self):
        return self._variables

    @property
    def parameters(self):
        return self._parameters

    @property
    def prolog_procedure(self):
        return self._prolog_procedure

    @prolog_procedure.setter
    def prolog_procedure(self, value):
        self._prolog_procedure = Process.add_generated_string_to_code(value)

    @property
    def metadata_procedure(self):
        return self._metadata_procedure

    @metadata_procedure.setter
    def metadata_procedure(self, value):
        self._metadata_procedure = Process.add_generated_string_to_code(value)

    @property
    def data_procedure(self):
        return self._data_procedure

    @data_procedure.setter
    def data_procedure(self, value):
        self._data_procedure = Process.add_generated_string_to_code(value)

    @property
    def epilog_procedure(self):
        return self._epilog_procedure

    @epilog_procedure.setter
    def epilog_procedure(self, value):
        self._epilog_procedure = Process.add_generated_string_to_code(value)

    @property
    def datasource_type(self):
        return self._datasource_type

    @datasource_type.setter
    def datasource_type(self, value):
        self._datasource_type = value

    @property
    def datasource_ascii_decimal_separator(self):
        return self._datasource_ascii_decimal_separator

    @datasource_ascii_decimal_separator.setter
    def datasource_ascii_decimal_separator(self, value):
        self._datasource_ascii_decimal_separator = value

    @property
    def datasource_ascii_delimiter_char(self):
        return self._datasource_ascii_delimiter_char

    @datasource_ascii_delimiter_char.setter
    def datasource_ascii_delimiter_char(self, value):
        self._datasource_ascii_delimiter_char = value

    @property
    def datasource_ascii_delimiter_type(self):
        return self._datasource_ascii_delimiter_type

    @datasource_ascii_delimiter_type.setter
    def datasource_ascii_delimiter_type(self, value):
        self._datasource_ascii_delimiter_type = value

    @property
    def datasource_ascii_header_records(self):
        return self._datasource_ascii_header_records

    @datasource_ascii_header_records.setter
    def datasource_ascii_header_records(self, value):
        self._datasource_ascii_header_records = value

    @property
    def datasource_ascii_quote_character(self):
        return self._datasource_ascii_quote_character

    @datasource_ascii_quote_character.setter
    def datasource_ascii_quote_character(self, value):
        self._datasource_ascii_quote_character = value

    @property
    def datasource_ascii_thousand_separator(self):
        return self._datasource_ascii_thousand_separator

    @datasource_ascii_thousand_separator.setter
    def datasource_ascii_thousand_separator(self, value):
        self._datasource_ascii_thousand_separator = value

    @property
    def datasource_data_source_name_for_client(self):
        return self._datasource_data_source_name_for_client

    @datasource_data_source_name_for_client.setter
    def datasource_data_source_name_for_client(self, value):
        self._datasource_data_source_name_for_client = value

    @property
    def datasource_data_source_name_for_server(self):
        return self._datasource_data_source_name_for_server

    @datasource_data_source_name_for_server.setter
    def datasource_data_source_name_for_server(self, value):
        self._datasource_data_source_name_for_server = value

    @property
    def datasource_password(self):
        return self._datasource_password

    @datasource_password.setter
    def datasource_password(self, value):
        self._datasource_password = value

    @property
    def datasource_user_name(self):
        return self._datasource_user_name

    @datasource_user_name.setter
    def datasource_user_name(self, value):
        self._datasource_user_name = value

    @property
    def datasource_query(self):
        return self._datasource_query

    @datasource_query.setter
    def datasource_query(self, value):
        self._datasource_query = value

    @property
    def datasource_uses_unicode(self):
        return self._datasource_uses_unicode

    @datasource_uses_unicode.setter
    def datasource_uses_unicode(self, value):
        self._datasource_uses_unicode = value

    @property
    def datasource_view(self):
        return self._datasource_view

    @datasource_view.setter
    def datasource_view(self, value):
        self._datasource_view = value

    @property
    def datasource_subset(self):
        return self._datasource_subset

    @datasource_subset.setter
    def datasource_subset(self, value):
        self._datasource_subset = value

    def add_variable(self, name, type):
        """ add variable to the process

        :param name: -
        :param type: 'String' or 'Numeric'
        :return:
        """
        # variable consists of actual variable and UI-Information ('ignore','other', etc.)
        # 1. handle Variable info
        variable = {'Name': name,
                    'Type': type,
                    'Position': len(self._variables) + 1,
                    'StartByte': 0,
                    'EndByte': 0}
        self._variables.append(variable)
        # 2. handle UI info
        var_type = 33 if type == 'Numeric' else 32
        # '\r' !
        variable_ui_data = 'VarType=' + str(var_type) + '\r' + 'ColType=' + str(827) + '\r'
        """
        mapping VariableUIData:
            VarType 33 -> Numeric
            VarType 32 -> String
            ColType 827 -> Other
        """
        self._variables_ui_data.append(variable_ui_data)

    def remove_variable(self, name):
        for variable in self.variables:
            if variable['Name'] == name:
                self._variables.remove(variable)

    def add_parameter(self, name, prompt, value, parameter_type=None):
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

    def remove_parameter(self, name):
        for parameter in self.parameters:
            if parameter['Name'] == name:
                self._parameters.remove(parameter)

    def drop_parameter_types(self):
        for p in range(len(self.parameters)):
            if 'Type' in self.parameters[p]:
                del self.parameters[p]['Type']

    # construct self.body (json) from the class-attributes
    def _construct_body(self):
        # general parameters
        body_as_dict = {'Name': self._name,
                'PrologProcedure': self._prolog_procedure,
                'MetadataProcedure': self._metadata_procedure,
                'DataProcedure': self._data_procedure,
                'EpilogProcedure': self._epilog_procedure,
                'HasSecurityAccess': self._has_security_access,
                'UIData':self._ui_data,
                'DataSource': {},
                'Parameters': self._parameters,
                'Variables': self._variables,
                'VariablesUIData':self._variables_ui_data}

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
