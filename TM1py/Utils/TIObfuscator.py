from collections import OrderedDict
import re
import random

keywords = ["datasourcenameforserver",
            "datasourcenameforclient",
            "datasourcetype",
            "datasourceusername",
            "datasourcepassword",
            "datasourcequery",
            "datasourcecubeview",
            "datasourcedimensionsubset",
            "datasourceasciidelimiter",
            "datasourceasciidecimalseparator",
            "datasourceasciithousandseparator",
            "datasourceasciiquotecharacter",
            "datasourceasciiheaderrecords",
            "value_is_string",
            "nvalue",
            "svalue",
            "break",
            "Processbreak",
            "ProcessQuit",
            "onminorerrordoitemskip",
            "minorerrorlogmax",
            "datasourceodbocatalog",
            "datasourceodboconnectionstring",
            "datasourceodbocubename",
            "datasourceodbohierarchyname",
            "datasourceodbolocation",
            "datasourceodboprovider",
            "datasourceodbosapclientid",
            "datasourceodbosapclientlanguage",
            "PrologMinorErrorCount ",
            "MetadataMinorErrorCount",
            "DataMinorErrorCount",
            "EpilogMinorErrorCount",
            "ProcessReturnCode"]


def get_all_defined_variables(code):
    variables = []

    # regular expression to get defined variables :
    expression = r'\b[a-zA-Z0-9_$][\w$]*\b[ /t]*='

    # iterate through lines
    for part in code.split(';'):
        for line in part.split('\r\n'):
            if len(line.strip()) > 0 and line.strip()[0] != '#':
                result = re.search(expression, line)
                if result:
                    variable = result.group()
                    variable_clean = variable[:-1].strip()
                    variables.append(variable_clean.lower())
    return variables


def generate_unique_string(code):
    code_slim = code.replace(' ', '').lower()
    unique_string = 'tm1py'
    while True:
        if unique_string not in code_slim:
            return unique_string
        else:
            unique_string += chr(random.randint(97, 122))


def split_into_statements(code):
    """ code from one Tab. Code String must come Without Comment-lines !
    
    :param code: 
    :return: 
    """
    PATTERN = re.compile(r'''((?:[^;']|'[^']*')+)''')
    return PATTERN.split(code)[1::2]


def remove_generated_code(code):
    """ Remove The generated code lines that are in between # \*\*\* comments
    
    :param code: 
    :return: 
    """
    return re.sub(r"#\*\*\*\*Begin: Generated Statements(?s)(.*)#\*\*\*\*End: Generated Statements\*\*\*\*", '', code)


def remove_comment_lines(code):
    code = '\r\n'.join([line if len(line.strip()) > 0 and line.strip()[0] != '#' else ''
                        for line
                        in code.split('\r\n')])
    return code


def obfuscate_code(code, variable_mapping, unique_string):
    new_code = ''

    # Remove Generated Code from CodeTab
    code = remove_generated_code(code)

    # Remove Comments from Code
    code = remove_comment_lines(code)

    # convert '' to a unique string
    code = code.replace("''", unique_string)

    # split code by not in single quote wrapped ;
    statements = split_into_statements(code)
    for j, part in enumerate(statements):
        statement_lines = part.split('\r\n')
        for i, line in enumerate(statement_lines):
            line_slim = line.strip()
            # Line is empty or Comment
            if len(line_slim) == 0:
                pass
            # Line is actual code
            else:
                # make the rest one line
                line = ''.join(statement_lines[i:])
                # Case: No ' in the line
                if "'" not in line:
                    for variable in variable_mapping:
                        line = line.lower().replace(variable, variable_mapping[variable])
                    new_code += (line.replace(' ', '').replace('\t', '') + ';')
                # Case: line has ' in it
                else:
                    new_line = ''
                    positions = [m.start() for m in re.finditer("'", line)]
                    for k, position in enumerate(positions):
                        if k == 0:
                            part = line[0:position]
                        else:
                            part = line[positions[k-1]:position]
                            # Check if %variableName% is inside the string
                            for variable_name_old, variable_name_new in variable_mapping.items():
                                # replace %variableName% by b
                                case_insensitive_replace = re.compile(re.escape('%{}%'.format(variable_name_old)),
                                                                      re.IGNORECASE)
                                part = case_insensitive_replace.sub('%{}%'.format(variable_name_new), part)
                        if k % 2 == 0:
                            for variable in variable_mapping:
                                part = part.lower().replace(variable, variable_mapping[variable])
                            part = part.replace(' ', '').replace('\t', '')
                            new_line += part
                        else:
                            new_line += "{}".format(part)

                    # piece behind last single quote
                    last_piece = line[positions[-1]:]
                    for variable in variable_mapping:
                        last_piece = last_piece.lower().replace(variable, variable_mapping[variable])
                        last_piece = last_piece.lower().replace(' ', '').replace('\t', '')
                    new_line += last_piece

                    new_line += ';'
                    new_code += new_line
                    pass
                break
    # convert unique string back to ''
    new_code = new_code.replace(unique_string, "''")
    return new_code


def obfuscate_process(process, new_name=None):
    # Hard variables : keywords, parameters
    hard_variables = [keyword.lower() for keyword in keywords] + \
                     [param['Name'].lower() for param in process.parameters] + \
                     [var['Name'].lower() for var in process.variables]

    # new variables (a, b, c , d, ... zx, zy, zz)
    new_variables = []
    for i in range(97, 123, 1):
        new_variables.append('{}'.format(chr(i)))
        for j in range(97, 123, 1):
            new_variables.append('{}{}'.format(chr(i), chr(j)))
    new_variables.sort(key=lambda element: (len(element), element))

    # find all variables in code
    variable_mapping = OrderedDict()

    # iterate through all code sections - find variables and add them to the mapping
    for code in (process.prolog_procedure, process.metadata_procedure, process.data_procedure, process.epilog_procedure):
        old_variables = [variable for variable in get_all_defined_variables(code) if variable.lower() not in hard_variables]
        for variable in old_variables:
            if variable not in variable_mapping.keys():
                variable_mapping[variable] = new_variables[len(variable_mapping.keys())]

    # generate a unique chain of chars
    all_code = process.prolog_procedure + process.metadata_procedure + process.data_procedure + process.epilog_procedure
    unique_string = generate_unique_string(all_code)

    # Obfuscate !
    process.prolog_procedure = obfuscate_code(process.prolog_procedure, variable_mapping, unique_string)
    process.metadata_procedure = obfuscate_code(process.metadata_procedure, variable_mapping, unique_string)
    process.data_procedure = obfuscate_code(process.data_procedure, variable_mapping, unique_string)
    process.epilog_procedure = obfuscate_code(process.epilog_procedure, variable_mapping, unique_string)

    # assign new name
    if new_name:
        process.name = new_name
    return process
