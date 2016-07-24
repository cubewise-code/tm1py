from TM1py import TM1pyLogin, TM1pyQueries as TM1

from collections import OrderedDict
import re
import sys
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


def obfuscate_code(code, variable_mapping, unique_string):
    new_code = ''

    # convert '' to a unique string
    code = code.replace("''", unique_string)

    parts = code.split(';')
    for j, part in enumerate(parts):
        lines = part.split('\r\n')
        for i, line in enumerate(lines):
            line_slim = line.strip()
            # 1. Options - line is part of the generated code
            if '#****Begin: Generated Statements***' in line_slim or '#****End: Generated Statements****' in line_slim:
                new_code += (line_slim + '\r\n')
            # 2. Option - line is empty
            elif len(line_slim) == 0:
                pass
            # 3. Option - line is comment
            elif line_slim[0] == '#':
                pass
            # 4. Option - line is actual code
            else:
                # check if this line has comments in it
                no_more_comments_in_next_lines = True
                for line in lines[i:]:
                    line_slim = line.strip()
                    if line_slim[0] == '#':
                        no_more_comments_in_next_lines = False

                if no_more_comments_in_next_lines:
                    # make the rest one line
                    line = ''.join(lines[i:])
                    # now 3 Options -
                    # Option 1 : No ' in the line :)
                    if "'" not in line:
                        for variable in variable_mapping:
                            line = line.lower().replace(variable, variable_mapping[variable])
                        new_code += (line.replace(' ', '').replace('\t', '') + ';')

                    else:
                        new_line = ''
                        positions = [m.start() for m in re.finditer("'", line)]
                        for k, position in enumerate(positions):
                            if k == 0:
                                part = line[0:position]
                            else:
                                part = line[positions[k-1]:position]

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


def main(process_source, process_target):
    # TM1py handles connection with TM1
    login = TM1pyLogin.native('admin', 'Number22!')
    tm1 = TM1(ip='', port=8543, login=login, ssl=False)

    # get process as is
    p = tm1.get_process(process_source)

    # change name
    p.set_name(process_target)

    # Hard variables : keywords, parameters
    hard_variables = [keyword.lower() for keyword in keywords] + \
                     [param['Name'].lower() for param in p.parameters] + \
                     [var['Name'].lower() for var in p.variables]

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
    for code in (p.prolog_procedure, p.metadata_procedure, p.data_procedure, p.epilog_procedure):
        old_variables = [variable for variable in get_all_defined_variables(code) if variable.lower() not in hard_variables]
        for variable in old_variables:
            if variable not in variable_mapping.keys():
                variable_mapping[variable] = new_variables[len(variable_mapping.keys())]

    # generate a unique chain of chars
    all_code = p.prolog_procedure + p.metadata_procedure + p.data_procedure + p.epilog_procedure
    unique_string = generate_unique_string(all_code)

    # obfuscate !
    new_prolog = obfuscate_code(p.prolog_procedure, variable_mapping, unique_string)
    p.set_prolog_procedure(new_prolog)
    new_metadata = obfuscate_code(p.metadata_procedure, variable_mapping, unique_string)
    p.set_metadata_procedure(new_metadata)
    new_data = obfuscate_code(p.data_procedure, variable_mapping, unique_string)
    p.set_data_procedure(new_data)
    new_epilog = obfuscate_code(p.epilog_procedure, variable_mapping, unique_string)
    p.set_epilog_procedure(new_epilog)

    # create new process
    tm1.create_process(p)

    # logout
    tm1.logout()

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])


