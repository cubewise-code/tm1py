class DimensionSelection:
    """ Instances of this class to be passed to construct_mdx function

    """
    SUBSET = 1
    EXPRESSION = 2
    ITERABLE = 3

    def __init__(self, dimension_name, elements=None, subset=None, expression=None):
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
    return "".join(["{" if not expression.startswith("{") else "",
                    expression,
                    "}" if not expression.endswith("}") else ""])


def read_cube_name_from_mdx(mdx):
    """ Read the cube name from a valid MDX Query

    :param mdx: The MDX Query as String
    :return: String, name of a cube
    """
    mdx_trimmed = ''.join(mdx.split()).upper()
    post_start = mdx_trimmed.rfind("FROM[") + len("FROM[")
    pos_end = mdx_trimmed.find("]WHERE", post_start)
    # if pos_end is -1 it works too
    cube_name = mdx_trimmed[post_start:pos_end]
    return cube_name
