import warnings


class DimensionSelection:
    """ Instances of this class to be passed to construct_mdx function

    """
    SUBSET = 1
    EXPRESSION = 2
    ITERABLE = 3

    def __init__(self, dimension_name, elements=None, subset=None, expression=None):
        """
        Create a new subset.

        Args:
            self: (todo): write your description
            dimension_name: (str): write your description
            elements: (todo): write your description
            subset: (todo): write your description
            expression: (str): write your description
        """
        warnings.warn(
            f"class DimensionSelection will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
            DeprecationWarning,
            stacklevel=2)
        self.dimension_name = dimension_name
        self.selection_type = self.determine_selection_type(elements, subset, expression)
        if self.selection_type == self.SUBSET:
            self.expression = curly_braces(expression="Tm1SubsetToSet([{dimension}], '{subset}')".format(
                dimension=dimension_name,
                subset=subset))
        elif self.selection_type == self.EXPRESSION:
            self.expression = curly_braces(expression=expression)
        elif self.selection_type == self.ITERABLE:
            self.expression = curly_braces(expression=",".join(["[{}].[{}]".format(dimension_name, element)
                                                                for element
                                                                in elements]))
        elif not self.selection_type:
            self.expression = curly_braces(expression="TM1SubsetAll([{dimension}])".format(dimension=dimension_name))

    @staticmethod
    def determine_selection_type(elements=None, subset=None, expression=None):
        """
        Determine the type of a given selection.

        Args:
            elements: (todo): write your description
            subset: (todo): write your description
            expression: (todo): write your description
        """
        warnings.warn(
            f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
            DeprecationWarning,
            stacklevel=2)
        if elements is not None and subset is None and expression is None:
            return DimensionSelection.ITERABLE
        elif elements is None and subset is not None and expression is None:
            return DimensionSelection.SUBSET
        elif elements is None and subset is None and expression is not None:
            return DimensionSelection.EXPRESSION
        elif elements is None and subset is None and expression is None:
            return None
        else:
            raise ValueError("DimensionSelection constructor takes one type of selection only: "
                             "elements, subset or expression")


def construct_mdx_axis(dim_selections):
    """ Construct MDX for one Axis (Row or Column).
    Can have multiple dimensions stacked.

    :param dim_selections: instances of TM1py.Utils.MDXUtils.DimensionSelection
    :return: a valid MDX for an Axis
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    return "*".join(selection.expression
                    for selection
                    in dim_selections)


def construct_mdx(cube_name, rows, columns, contexts=None, suppress=None):
    """ Method to construct MDX Query from different dimension selection

    :param cube_name: Name of the Cube
    :param rows: List of DimensionSelections
    :param columns: List of DimensionSelections
    :param contexts: Dictionary of Dimensions and Elements
    :param suppress: "Both", "Rows", "Columns" or None
    :return: Generated MDX Query
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    # MDX Skeleton
    mdx_template = "SELECT {}{} ON ROWS, {}{} ON COLUMNS FROM [{}] {}"
    # Suppression
    mdx_rows_suppress = "NON EMPTY " if suppress and suppress.upper() in ["ROWS", "BOTH"] else ""
    mdx_columns_suppress = "NON EMPTY " if suppress and suppress.upper() in ["COLUMNS", "BOTH"] else ""
    # Rows and Columns
    mdx_rows = construct_mdx_axis(rows)
    mdx_columns = construct_mdx_axis(columns)
    # Context filter (where statement)
    mdx_where = ""
    if contexts:
        mdx_where_parts = ["[{}].[{}]".format(dim, elem)
                           for dim, elem
                           in contexts.items()]
        mdx_where = "".join(["WHERE (",
                             ",".join(mdx_where_parts),
                             ")"])
    # Return Full MDX
    return mdx_template.format(mdx_rows_suppress, mdx_rows, mdx_columns_suppress, mdx_columns, cube_name, mdx_where)


def curly_braces(expression):
    """ Put curly braces around a string

    :param expression:
    :return:
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    return "".join(["{" if not expression.startswith("{") else "",
                    expression,
                    "}" if not expression.endswith("}") else ""])


def read_cube_name_from_mdx(mdx):
    """ Read the cube name from a valid MDX Query

    :param mdx: The MDX Query as String
    :return: String, name of a cube
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    cube, _, _, _ = read_dimension_composition_from_mdx(mdx)
    return cube


def read_dimension_composition_from_mdx(mdx):
    """ Parse a valid MDX Query and return the name of the cube and a list of dimensions for each axis

    :param mdx:
    :return:
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    mdx_rows, mdx_columns, mdx_from, mdx_where = split_mdx(mdx)

    cube = mdx_from[1:-1]
    rows = read_dimension_composition_from_mdx_set_or_tuple(mdx_rows)
    columns = read_dimension_composition_from_mdx_set_or_tuple(mdx_columns)
    titles = read_dimension_composition_from_mdx_set_or_tuple(mdx_where)

    return cube, rows, columns, titles


def read_dimension_composition_from_mdx_set_or_tuple(mdx):
    """
    Read the composition of a composition.

    Args:
        mdx: (str): write your description
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    mdx_without_spaces = ''.join(mdx.split())
    # case for mdx statement no where statement
    if len(mdx_without_spaces) == 0:
        return []
    # case for tuples mdx statement on rows or columns
    if mdx_without_spaces[1] == '(' and mdx_without_spaces[-2] == ')':
        return read_dimension_composition_from_mdx_tuple(mdx)
    # case for where mdx statement
    elif mdx_without_spaces[0] == '(' and mdx_without_spaces[-1] == ')':
        return read_dimension_composition_from_mdx_tuple(mdx)
    # case for set mdx statement on rows or columns
    else:
        return read_dimension_composition_from_mdx_set(mdx)


def read_dimension_composition_from_mdx_set(mdx):
    """
    Read a list of the composition from a list of mdx.

    Args:
        mdx: (str): write your description
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    dimensions = []
    mdx_without_spaces = ''.join(mdx.split())
    for sub_mdx in mdx_without_spaces.split("}*{"):
        pos_start, pos_end = sub_mdx.find("["), sub_mdx.find("]")
        dimension_name = sub_mdx[pos_start + 1:pos_end]
        dimensions.append(dimension_name)
    return dimensions


def read_dimension_composition_from_mdx_tuple(mdx):
    """
    Reads a list from a member.

    Args:
        mdx: (str): write your description
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    dimensions = []
    for unique_member_name in mdx.split(","):
        pos_start, pos_end = unique_member_name.find("["), unique_member_name.find("]")
        dimension_name = unique_member_name[pos_start + 1:pos_end]
        # only parse through first tuple of potentially many tuples
        if dimension_name in dimensions:
            return dimensions
        dimensions.append(dimension_name)
    return dimensions


def split_mdx(mdx):
    """
    Split markdown text into two columns.

    Args:
        mdx: (str): write your description
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    try:
        mdx_rows, mdx_rest = _find_case_and_space_insensitive_first_occurrence(
            text=mdx,
            pattern_start="{",
            pattern_end="}ONROWS"
        )
        mdx_columns, mdx_rest = _find_case_and_space_insensitive_first_occurrence(
            text=mdx_rest,
            pattern_start="{",
            pattern_end="}ONCOLUMNSFROM"
        )
        mdx_from, mdx_where = _find_case_and_space_insensitive_first_occurrence(
            text=mdx_rest,
            pattern_end="]WHERE"
        )
        return mdx_rows, mdx_columns, mdx_from, mdx_where
    except ValueError:
        ValueError("Can't parse mdx: {}".format(mdx))


def _find_case_and_space_insensitive_first_occurrence(text, pattern_start=None, pattern_end=None):
    """
    Find the index and last occurrence of the text.

    Args:
        text: (str): write your description
        pattern_start: (str): write your description
        pattern_end: (str): write your description
    """
    warnings.warn(
        f"Module MdxUtils will be deprecated. Use https://github.com/cubewise-code/mdxpy instead",
        DeprecationWarning,
        stacklevel=2)
    text_without_spaces = ''.join(text.split())
    text_without_spaces_and_uppercase = text_without_spaces.upper()

    if pattern_start:
        pattern_start = ''.join(pattern_start.split()).upper()
    if pattern_end:
        pattern_end = ''.join(pattern_end.split()).upper()

    if text_without_spaces_and_uppercase.count(pattern_end) > 1:
        raise ValueError("Invalid state. {} has more than 1 occurrences in text: {}".format(pattern_end, text))
    pos_start = text_without_spaces_and_uppercase.find(pattern_start) if pattern_start else 0
    pos_end = text_without_spaces_and_uppercase.find(pattern_end) if pattern_end else -1

    # case of mdx statement without where clause
    if pos_start == 0 and pos_end == -1:
        return text, ""
    selection = text_without_spaces[pos_start:pos_end + 1]
    text = text_without_spaces[pos_end + len(pattern_end):]
    return selection, text
